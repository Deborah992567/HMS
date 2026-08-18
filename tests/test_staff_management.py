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

    db = TestingSessionLocal()
    try:
        admin_role = Role(name="Admin")
        db.add(admin_role)
        db.commit()
        db.refresh(admin_role)

        admin_user = Staff(name="Admin User", email="admin2@example.com", hashed_password=get_password_hash("secret"))
        admin_user.roles = [admin_role]
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)

        # create a non-admin user so token maps to an existing user (for 403 checks)
        normal_user = Staff(name="Normal User", email="normal@example.com", hashed_password=get_password_hash("pw"))
        db.add(normal_user)
        db.commit()
        db.refresh(normal_user)
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


def test_list_update_delete_staff(test_app):
    client = test_app
    token = create_access_token({"user_id": 1, "roles": ["Admin"]})
    headers = {"Authorization": f"Bearer {token}"}

    # list staff
    res = client.get("/api/staff/", headers=headers)
    assert res.status_code == 200
    staff_list = res.json()
    assert any(s["email"] == "admin2@example.com" for s in staff_list)

    # update admin name
    res_up = client.put("/api/staff/1", json={"name": "Administrator"}, headers=headers)
    assert res_up.status_code == 200
    assert res_up.json()["name"] == "Administrator"

    # delete staff (create a user then delete)
    res_create = client.post("/api/staff/", json={"name": "ToDelete", "email": "del@x.com", "password": "pw", "role_ids": []}, headers=headers)
    assert res_create.status_code == 200
    new_id = res_create.json()["id"]

    res_del = client.delete(f"/api/staff/{new_id}", headers=headers)
    assert res_del.status_code == 200

    # forbidden for non-admin
    token2 = create_access_token({"user_id": 2, "roles": []})
    headers2 = {"Authorization": f"Bearer {token2}"}
    res_forbid = client.get("/api/staff/", headers=headers2)
    assert res_forbid.status_code == 403
