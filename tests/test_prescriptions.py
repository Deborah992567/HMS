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
        doc_role = Role(name="Doctor")
        pharm_role = Role(name="Pharmacist")
        db.add_all([doc_role, pharm_role])
        db.commit()
        db.refresh(doc_role)

        doc = Staff(name="Dr Rx", email="drx@example.com", hashed_password=get_password_hash("pw"))
        doc.roles = [doc_role]
        pharm = Staff(name="Pharm", email="pharm@example.com", hashed_password=get_password_hash("pw"))
        pharm.roles = [pharm_role]
        db.add_all([doc, pharm])

        patient = Patient(name="Presc Patient", email="pp@example.com")
        db.add(patient)
        db.commit()
        db.refresh(doc)
        db.refresh(pharm)
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


def test_create_and_fulfill_prescription(test_app):
    client = test_app
    token = create_access_token({"user_id": 1, "roles": ["Doctor"]})
    headers = {"Authorization": f"Bearer {token}"}

    payload = {"patient_id": 1, "doctor_id": 1, "medication": "DrugA", "dosage": "1x/day", "instructions": "Take with food"}
    res = client.post("/api/prescriptions/", json=payload, headers=headers)
    assert res.status_code == 200
    presc = res.json()
    assert presc["medication"] == "DrugA"

    # fulfill as pharmacist
    token_ph = create_access_token({"user_id": 2, "roles": ["Pharmacist"]})
    headers_ph = {"Authorization": f"Bearer {token_ph}"}
    res_f = client.post(f"/api/prescriptions/{presc['id']}/fulfill", headers=headers_ph)
    assert res_f.status_code == 200
    assert res_f.json()["fulfilled"] is True
