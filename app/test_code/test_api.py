import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool  # ← 追加
from app.back.database import Base, get_db
from app.back.main import app

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,  # ← 追加
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture()
def client():
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=engine)

def signup_and_login(client, username="testuser", password="testpass"):
    client.post("/api/auth/signup", json={"username": username, "password": password})
    client.post("/api/auth/login", json={"username": username, "password": password})

def create_test_group(client, name="テストグループ", is_lock=False, password=""):
    me = client.get("/api/auth/me").json()
    return client.post("/api/groups/", json={
        "name": name,
        "owner": me["id"],
        "is_lock": is_lock,
        "password": password,
        "title": "リーダブルコード",
        "total_pages": 237,
    })

class TestAuth:
    def test_signup(self, client):
        res = client.post("/api/auth/signup", json={"username": "user1", "password": "pass1"})
        assert res.status_code == 200
        assert res.json()["username"] == "user1"
        assert "password_hash" not in res.json()

    def test_signup_duplicate(self, client):
        client.post("/api/auth/signup", json={"username": "user1", "password": "pass1"})
        res = client.post("/api/auth/signup", json={"username": "user1", "password": "pass1"})
        assert res.status_code == 400

    def test_login_success(self, client):
        client.post("/api/auth/signup", json={"username": "user1", "password": "pass1"})
        res = client.post("/api/auth/login", json={"username": "user1", "password": "pass1"})
        assert res.status_code == 200
        assert res.json()["message"] == "ログインしました"

    def test_login_wrong_password(self, client):
        client.post("/api/auth/signup", json={"username": "user1", "password": "pass1"})
        res = client.post("/api/auth/login", json={"username": "user1", "password": "wrong"})
        assert res.status_code == 400

    def test_me_authenticated(self, client):
        signup_and_login(client, "user1", "pass1")
        res = client.get("/api/auth/me")
        assert res.status_code == 200
        assert res.json()["username"] == "user1"

    def test_me_unauthenticated(self, client):
        res = client.get("/api/auth/me")
        assert res.status_code == 401

    def test_logout(self, client):
        signup_and_login(client, "user1", "pass1")
        res = client.post("/api/auth/logout")
        assert res.status_code == 200
        res = client.get("/api/auth/me")
        assert res.status_code == 401

class TestGroup:
    def test_create_group(self, client):
        signup_and_login(client)
        res = create_test_group(client)
        assert res.status_code == 200
        assert res.json()["name"] == "テストグループ"
        assert res.json()["title"] == "リーダブルコード"

    def test_get_all_groups(self, client):
        signup_and_login(client)
        create_test_group(client, "グループA")
        create_test_group(client, "グループB")
        res = client.get("/api/groups/")
        assert res.status_code == 200
        assert len(res.json()) == 2

    def test_get_group_by_id(self, client):
        signup_and_login(client)
        group_id = create_test_group(client).json()["id"]
        res = client.get(f"/api/groups/{group_id}")
        assert res.status_code == 200
        assert res.json()["id"] == group_id

    def test_get_group_not_found(self, client):
        signup_and_login(client)
        res = client.get("/api/groups/999")
        assert res.status_code == 404

    def test_search_by_name(self, client):
        signup_and_login(client)
        create_test_group(client, "Python読書会")
        create_test_group(client, "Rust勉強会")
        res = client.get("/api/groups/search/by-name?q=Python")
        assert res.status_code == 200
        assert len(res.json()) == 1
        assert res.json()[0]["name"] == "Python読書会"

    def test_search_by_book(self, client):
        signup_and_login(client)
        create_test_group(client, "グループA")
        res = client.get("/api/groups/search/by-book?q=リーダブル")
        assert res.status_code == 200
        assert len(res.json()) == 1

    def test_search_not_found(self, client):
        signup_and_login(client)
        res = client.get("/api/groups/search/by-name?q=存在しない")
        assert res.status_code == 404

class TestMembership:
    def test_join_unlocked_group(self, client):
        signup_and_login(client)
        group_id = create_test_group(client, is_lock=False).json()["id"]
        signup_and_login(client, "user2", "pass2")
        res = client.post(f"/api/groups/{group_id}/join")
        assert res.status_code == 200

    def test_join_locked_group_correct_password(self, client):
        signup_and_login(client)
        group_id = create_test_group(client, is_lock=True, password="secret").json()["id"]
        signup_and_login(client, "user2", "pass2")
        res = client.post(f"/api/groups/{group_id}/join?password=secret")
        assert res.status_code == 200

    def test_join_locked_group_wrong_password(self, client):
        signup_and_login(client)
        group_id = create_test_group(client, is_lock=True, password="secret").json()["id"]
        signup_and_login(client, "user2", "pass2")
        res = client.post(f"/api/groups/{group_id}/join?password=wrong")
        assert res.status_code == 400

    def test_join_duplicate(self, client):
        signup_and_login(client)
        group_id = create_test_group(client, is_lock=False).json()["id"]
        client.post(f"/api/groups/{group_id}/join")
        res = client.post(f"/api/groups/{group_id}/join")
        assert res.status_code == 400

    def test_leave_group(self, client):
        signup_and_login(client)
        group_id = create_test_group(client, is_lock=False).json()["id"]
        signup_and_login(client, "user2", "pass2")
        client.post(f"/api/groups/{group_id}/join")
        res = client.post(f"/api/groups/{group_id}/leave")
        assert res.status_code == 200

    def test_owner_cannot_leave(self, client):
        signup_and_login(client)
        group_id = create_test_group(client).json()["id"]
        res = client.post(f"/api/groups/{group_id}/leave")
        assert res.status_code == 400

    def test_my_groups(self, client):
        signup_and_login(client)
        group_id = create_test_group(client, is_lock=False).json()["id"]
        signup_and_login(client, "user2", "pass2")
        client.post(f"/api/groups/{group_id}/join")
        res = client.get("/api/groups/my-list")
        assert res.status_code == 200
        assert len(res.json()) == 1

class TestProgress:
    def test_create_progress(self, client):
        signup_and_login(client)
        group_id = create_test_group(client).json()["id"]
        res = client.post(f"/api/groups/{group_id}/progress", json={
            "start_page": 1,
            "end_page": 50,
            "memo": "第1章完了"
        })
        assert res.status_code == 200
        assert res.json()["start_page"] == 1
        assert res.json()["end_page"] == 50

    def test_get_progresses(self, client):
        signup_and_login(client)
        group_id = create_test_group(client).json()["id"]
        client.post(f"/api/groups/{group_id}/progress", json={"start_page": 1, "end_page": 50})
        client.post(f"/api/groups/{group_id}/progress", json={"start_page": 51, "end_page": 100})
        res = client.get(f"/api/groups/{group_id}/progress")
        assert res.status_code == 200
        assert len(res.json()) == 2

    def test_progress_invalid_group(self, client):
        signup_and_login(client)
        res = client.post("/api/groups/999/progress", json={"start_page": 1, "end_page": 50})
        assert res.status_code == 404