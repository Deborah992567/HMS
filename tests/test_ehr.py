import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# ensure project root is on sys.path for imports when running tests
ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from database import Base, get_db
from main import app
from utils import get_password_hash, create_access_token
from models import Role, Staff, Patient


SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="module")
def test_app():
    from sqlalchemy.pool import StaticPool
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    try:
        doctor_role = Role(name="Doctor")
        db.add(doctor_role)
        db.commit()
        db.refresh(doctor_role)

        doc = Staff(name="Dr Test", email="drtest@example.com", hashed_password=get_password_hash("pw"))
        doc.roles = [doctor_role]
        db.add(doc)

        patient = Patient(name="Bob", email="bob@example.com")
        db.add(patient)
        db.commit()
        db.refresh(doc)
        db.refresh(patient)
    finally:
        db.close()

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client


def test_create_ehr_and_chain_record(test_app):
    client = test_app
    token = create_access_token({"user_id": 1, "roles": ["Doctor"]})
    headers = {"Authorization": f"Bearer {token}"}

    payload = {"patient_id": 1, "diagnosis": "Flu", "medication": "Rest", "notes": "Keep hydrated"}
    res = client.post("/api/ehr/", json=payload, headers=headers)
    assert res.status_code == 200
    ehr = res.json()
    assert ehr["diagnosis"] == "Flu"

    # mine a block so the transaction is committed, then check blockchain recorded transaction
    mine_res = client.get("/api/blockchain/mine")
    assert mine_res.status_code == 200
    chain_res = client.get("/api/blockchain/chain")
    assert chain_res.status_code == 200
    chain = chain_res.json().get('chain', [])
    # genesis + 1 mined blocks maybe — ensure some transactions exist with type EHR
    from blockchain import blockchain as bc
    txs = []
    for block in chain:
        for tx in block.get("transactions", []):
            txs.append(tx)

    # find any encrypted transaction that decrypts to an EHR marker
    found = False
    for t in txs:
        enc = t.get('data_encrypted')
        if enc:
            try:
                data = bc.decrypt_data(enc)
                if isinstance(data, dict) and data.get('type') == 'EHR':
                    found = True
                    break
            except Exception:
                continue
    assert found
