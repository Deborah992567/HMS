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
from models import Role, Staff, Patient, Doctor


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
        # create roles
        admin_role = Role(name="Admin")
        rec_role = Role(name="Reception")
        doc_role = Role(name="Doctor")
        db.add_all([admin_role, rec_role, doc_role])
        db.commit()
        db.refresh(admin_role)
        db.refresh(rec_role)
        db.refresh(doc_role)

        # create users
        admin = Staff(name="Admin", email="a@x.com", hashed_password=get_password_hash("pw"))
        admin.roles = [admin_role]
        rec = Staff(name="Rec", email="r@x.com", hashed_password=get_password_hash("pw"))
        rec.roles = [rec_role]
        doc_user = Staff(name="DocUser", email="d@x.com", hashed_password=get_password_hash("pw"))
        doc_user.roles = [doc_role]
        db.add_all([admin, rec, doc_user])
        db.commit()

        # create doctor and patient
        doctor = Doctor(name="Dr Who", specialty="General")
        patient = Patient(name="Patient One", email="p1@example.com")
        db.add_all([doctor, patient])
        db.commit()
        db.refresh(doctor)
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


def test_create_appointment_and_conflict(test_app):
    client = test_app
    # receptionist token (user id 2)
    token = create_access_token({"user_id": 2, "roles": ["Reception"]})
    headers = {"Authorization": f"Bearer {token}"}

    date = datetime.utcnow().isoformat()
    payload = {"date": date, "patient_id": 1, "doctor_id": 1}
    res = client.post("/api/appointments/", json=payload, headers=headers)
    assert res.status_code == 200

    # try to create conflicting appointment for same doctor at same time
    res2 = client.post("/api/appointments/", json=payload, headers=headers)
    assert res2.status_code == 400
