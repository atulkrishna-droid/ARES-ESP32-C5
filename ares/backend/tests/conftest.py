"""Pytest test configuration and fixtures."""
import os
import sys
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import Base, get_db
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.case import Case
from app.models.device import Device, DeviceAuthorization
from app.models.hardware_profile import HardwareProfile
from app.models.user import Permission, Role, User

# In-memory test SQLite database
TEST_DB_URL = "sqlite:///:memory:"
test_engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db_session():
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def seeded_users(db_session):
    # Create granular permissions
    perm_names = [
        ("*", "All permissions", "ADMIN"),
        ("case.read", "Read cases", "CASE"),
        ("case.write", "Write cases", "CASE"),
        ("assessment.create", "Create assessments", "ASSESSMENT"),
        ("assessment.start", "Start assessments", "ASSESSMENT"),
        ("assessment.stop", "Stop assessments", "ASSESSMENT"),
        ("assessment.read", "Read assessments", "ASSESSMENT"),
        ("assessment.write", "Update assessments", "ASSESSMENT"),
        ("device.read", "Read devices", "DEVICE"),
        ("device.enroll", "Enroll devices", "DEVICE"),
        ("device.authorize", "Authorize devices", "DEVICE"),
        ("device.revoke", "Revoke devices", "DEVICE"),
        ("esp32.read", "Read ESP32", "ESP32"),
        ("esp32.scan", "ESP32 scans", "ESP32"),
        ("esp32.connect", "ESP32 control", "ESP32"),
        ("evidence.create", "Create evidence", "EVIDENCE"),
        ("evidence.read", "Read evidence", "EVIDENCE"),
        ("report.generate", "Generate reports", "REPORT"),
        ("report.read", "Read reports", "REPORT"),
        ("audit.read", "Read audit logs", "AUDIT"),
        ("lab.execute", "Execute lab scenarios", "LAB"),
    ]
    perms_map = {}
    for p_name, p_desc, p_cat in perm_names:
        p = Permission(name=p_name, description=p_desc, category=p_cat)
        db_session.add(p)
        perms_map[p_name] = p
    db_session.flush()

    admin_role = Role(name="ADMIN")
    admin_role.permissions.append(perms_map["*"])

    analyst_role = Role(name="ANALYST")
    for p_name in ["case.read", "case.write", "assessment.create", "assessment.start", "assessment.stop",
                   "assessment.read", "assessment.write", "device.read", "device.enroll", "esp32.read",
                   "esp32.scan", "evidence.create", "evidence.read", "report.generate", "report.read"]:
        analyst_role.permissions.append(perms_map[p_name])

    viewer_role = Role(name="VIEWER")
    for p_name in ["case.read", "assessment.read", "report.read", "device.read"]:
        viewer_role.permissions.append(perms_map[p_name])

    lab_user_role = Role(name="LAB_USER")
    for p_name in ["lab.execute", "device.read", "assessment.read"]:
        lab_user_role.permissions.append(perms_map[p_name])

    db_session.add_all([admin_role, analyst_role, viewer_role, lab_user_role])
    db_session.flush()

    admin = User(
        email="admin@test.internal",
        username="admin",
        password_hash=hash_password("AdminPass123!"),
        is_active=True,
        is_verified=True,
    )
    admin.roles.append(admin_role)

    analyst = User(
        email="analyst@test.internal",
        username="analyst",
        password_hash=hash_password("AnalystPass123!"),
        is_active=True,
        is_verified=True,
    )
    analyst.roles.append(analyst_role)

    viewer = User(
        email="viewer@test.internal",
        username="viewer",
        password_hash=hash_password("ViewerPass123!"),
        is_active=True,
        is_verified=True,
    )
    viewer.roles.append(viewer_role)

    lab_user = User(
        email="labuser@test.internal",
        username="lab_user",
        password_hash=hash_password("LabUserPass123!"),
        is_active=True,
        is_verified=True,
    )
    lab_user.roles.append(lab_user_role)

    db_session.add_all([admin, analyst, viewer, lab_user])
    db_session.commit()

    return {"admin": admin, "analyst": analyst, "viewer": viewer, "lab_user": lab_user}


@pytest.fixture
def admin_headers(seeded_users):
    admin = seeded_users["admin"]
    token = create_access_token(
        subject=admin.id,
        roles=["ADMIN"],
        permissions=["*"],
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def viewer_headers(seeded_users):
    viewer = seeded_users["viewer"]
    token = create_access_token(
        subject=viewer.id,
        roles=["VIEWER"],
        permissions=["case.read", "assessment.read"],
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers(seeded_users):
    headers = {}
    for role_key, user in seeded_users.items():
        perms = user.permission_names
        if role_key == "admin":
            perms = ["*"]
        token = create_access_token(
            subject=user.id,
            roles=[r.name for r in user.roles],
            permissions=perms,
        )
        headers[role_key] = {"Authorization": f"Bearer {token}"}
    return headers
