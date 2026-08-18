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
        admin_role = Role(name="Admin")
        db.add_all([doc_role, admin_role])
        db.commit()
        db.refresh(doc_role)

        doc = Staff(name="Dr Core", email="drcore@example.com", hashed_password=get_password_hash("pw"))
        doc.roles = [doc_role]
        admin = Staff(name="Admin User", email="admin@example.com", hashed_password=get_password_hash("pw"))
        admin.roles = [admin_role]
        db.add_all([doc, admin])

        patient = Patient(name="EHR Patient", email="ehrp@example.com")
        db.add(patient)
        db.commit()
        db.refresh(doc)
        db.refresh(admin)
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


def test_ehr_versioning_and_access(test_app):
    client = test_app
    token = create_access_token({"user_id": 1, "roles": ["Doctor"]})
    headers = {"Authorization": f"Bearer {token}"}

    payload = {"patient_id": 1, "diagnosis": "Initial", "medication": "MedA", "notes": "note1"}
    res = client.post("/api/ehr/", json=payload, headers=headers)
    assert res.status_code == 200
    ehr = res.json()
    assert ehr["diagnosis"] == "Initial"

    # update
    payload2 = {"patient_id": 1, "diagnosis": "Updated", "medication": "MedB", "notes": "note2"}
    res2 = client.put(f"/api/ehr/{ehr['id']}", json=payload2, headers=headers)
    assert res2.status_code == 200
    updated = res2.json()
    assert updated["diagnosis"] == "Updated"

    # list versions
    resv = client.get(f"/api/ehr/{ehr['id']}/versions", headers=headers)
    assert resv.status_code == 200
    versions = resv.json()
    assert len(versions) >= 1

    # Admin can also view versions
    token_admin = create_access_token({"user_id": 2, "roles": ["Admin"]})
    headers_admin = {"Authorization": f"Bearer {token_admin}"}
    resv2 = client.get(f"/api/ehr/{ehr['id']}/versions", headers=headers_admin)
    assert resv2.status_code == 200

