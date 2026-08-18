import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta

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
        admin_role = Role(name="Admin")
        doc_role = Role(name="Doctor")
        rec_role = Role(name="Reception")
        db.add_all([admin_role, doc_role, rec_role])
        db.commit()
        db.refresh(admin_role)

        admin = Staff(name="Admin", email="a2@x.com", hashed_password=get_password_hash("pw"))
        admin.roles = [admin_role]
        doc_user = Staff(name="DocUser", email="d2@x.com", hashed_password=get_password_hash("pw"))
        doc_user.roles = [doc_role]
        rec = Staff(name="Rec", email="r2@x.com", hashed_password=get_password_hash("pw"))
        rec.roles = [rec_role]
        db.add_all([admin, doc_user, rec])
        db.commit()

        doctor = Doctor(name="Dr Strange", specialty="Surgery")
        patient = Patient(name="Patient Two", email="p2@example.com")
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


def test_set_availability_and_booking(test_app):
    client = test_app
    admin_token = create_access_token({"user_id": 1, "roles": ["Admin"]})
    headers = {"Authorization": f"Bearer {admin_token}"}

    start = datetime.utcnow() + timedelta(days=1)
    end = start + timedelta(hours=8)
    payload = {"doctor_id": 1, "start_time": start.isoformat(), "end_time": end.isoformat()}
    res = client.post("/api/doctors/1/availability", json=payload, headers=headers)
    assert res.status_code == 200

    # receptionist books within availability
    rec_token = create_access_token({"user_id": 3, "roles": ["Reception"]})
    headers_rec = {"Authorization": f"Bearer {rec_token}"}
    appt_time = start + timedelta(hours=1)
    appt_payload = {"date": appt_time.isoformat(), "patient_id": 1, "doctor_id": 1}
    res2 = client.post("/api/appointments/", json=appt_payload, headers=headers_rec)
    assert res2.status_code == 200

    # cancel appointment
    appt_id = res2.json()["id"]
    res_cancel = client.put(f"/api/appointments/{appt_id}/cancel", headers=headers_rec)
    assert res_cancel.status_code == 200
    assert res_cancel.json()["status"] == "cancelled"
