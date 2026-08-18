import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime

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
        admin_role = Role(name="Admin")
        db.add(admin_role)
        db.commit()
        db.refresh(admin_role)

        admin = Staff(name="AdminC", email="adminc@example.com", hashed_password=get_password_hash("pw"))
        admin.roles = [admin_role]
        db.add(admin)

        patient = Patient(name="ConsentPatient", email="cp@example.com")
        db.add(patient)
        db.commit()
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


def test_grant_and_revoke_consent(test_app):
    client = test_app
    token = create_access_token({"user_id": 1, "roles": ["Admin"]})
    headers = {"Authorization": f"Bearer {token}"}

    payload = {"patient_id": 1, "granted_to": "research", "scope": "deidentified"}
    res = client.post("/api/consents/", json=payload, headers=headers)
    assert res.status_code == 200
    cons = res.json()
    assert cons["granted_to"] == "research"

    res_revoke = client.post(f"/api/consents/{cons['id']}/revoke", headers=headers)
    assert res_revoke.status_code == 200
    assert res_revoke.json()["revoked"] is True
