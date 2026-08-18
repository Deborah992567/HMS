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
from models import Role, Staff


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

    # create initial admin user directly
    db = TestingSessionLocal()
    try:
        admin_role = Role(name="Admin")
        db.add(admin_role)
        db.commit()
        db.refresh(admin_role)

        admin_user = Staff(name="Admin User", email="admin@example.com", hashed_password=get_password_hash("secret"))
        admin_user.roles = [admin_role]
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
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


def test_create_role_and_staff_with_admin(test_app):
    client = test_app
    # create token for admin user
    token = create_access_token({"user_id": 1, "roles": ["Admin"]})
    headers = {"Authorization": f"Bearer {token}"}

    # create a new role
    res = client.post("/api/roles/", json={"name": "Reception"}, headers=headers)
    assert res.status_code == 200
    role = res.json()
    assert role["name"] == "Reception" or role.get("name") == "Reception"

    # create a staff member with the new role
    res2 = client.post("/api/staff/", json={"name": "Receptionist", "email": "recp@example.com", "password": "pw123", "role_ids": [role["id"]]}, headers=headers)
    assert res2.status_code == 200
    staff = res2.json()
    assert staff["email"] == "recp@example.com"
    assert any(r["name"] == "Reception" for r in staff.get("roles", []))


def test_role_creation_forbidden_for_non_admin(test_app):
    client = test_app
    # token for non-admin (no roles)
    token = create_access_token({"user_id": 2, "roles": []})
    headers = {"Authorization": f"Bearer {token}"}

    res = client.post("/api/roles/", json={"name": "X"}, headers=headers)
    assert res.status_code == 403
