import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool  
from app.back.database import Base, get_db
from app.back.main import app
from app.back.crud import format_activity_time

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,  
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

class TestGroupUpdate:
    def test_update_name(self, client):
        signup_and_login(client)
        group_id = create_test_group(client).json()["id"]
        res = client.patch(f"/api/groups/{group_id}", json={"name": "新しいグループ名"})
        assert res.status_code == 200
        assert res.json()["name"] == "新しいグループ名"

    def test_update_is_lock(self, client):
        signup_and_login(client)
        group_id = create_test_group(client, is_lock=False).json()["id"]
        res = client.patch(f"/api/groups/{group_id}", json={"is_lock": True})
        assert res.status_code == 200
        assert res.json()["is_lock"] == True

    def test_update_password(self, client):
        """パスワード変更後に新パスワードで参加できること"""
        signup_and_login(client)
        group_id = create_test_group(client, is_lock=True, password="old").json()["id"]
        client.patch(f"/api/groups/{group_id}", json={"password": "new"})
        signup_and_login(client, "user2", "pass2")
        res = client.post(f"/api/groups/{group_id}/join?password=new")
        assert res.status_code == 200

    def test_update_by_non_owner(self, client):
        """オーナー以外は更新できないこと"""
        signup_and_login(client)
        group_id = create_test_group(client).json()["id"]
        signup_and_login(client, "user2", "pass2")
        res = client.patch(f"/api/groups/{group_id}", json={"name": "乗っ取り"})
        assert res.status_code == 403

    def test_update_nonexistent_group(self, client):
        signup_and_login(client)
        res = client.patch("/api/groups/999", json={"name": "存在しない"})
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

    def test_get_progresses_with_limit(self, client):
        signup_and_login(client)
        group_id = create_test_group(client).json()["id"]
        # 25件登録
        for i in range(25):
            client.post(f"/api/groups/{group_id}/progress", json={"start_page": i+1, "end_page": i+1})
        # limitなしは25件
        res = client.get(f"/api/groups/{group_id}/progress")
        assert res.status_code == 200
        assert len(res.json()) == 25
        # limit=20は20件
        res = client.get(f"/api/groups/{group_id}/progress?limit=20")
        assert res.status_code == 200
        assert len(res.json()) == 20

    def test_get_progresses_order(self, client):
        """idの降順（新しい順）で返ってくること"""
        signup_and_login(client)
        group_id = create_test_group(client).json()["id"]
        res1 = client.post(f"/api/groups/{group_id}/progress", json={"start_page": 1, "end_page": 10})
        res2 = client.post(f"/api/groups/{group_id}/progress", json={"start_page": 11, "end_page": 20})
        res = client.get(f"/api/groups/{group_id}/progress")
        assert res.status_code == 200
        progresses = res.json()
        # idが大きい方（後に作成）が先頭
        assert progresses[0]["id"] > progresses[1]["id"]

class TestProgressActivity:
    def test_activities_only_joined_groups_and_exclude_initial_progress(self, client):
        """参加中グループの通常進捗だけをアクティビティとして返す"""
        # user1が参加しているグループを作成し、表示対象になる通常進捗を追加する。
        # グループ作成時の初期進捗も自動作成されるが、それは後続の検証で除外される想定。
        signup_and_login(client, "user1", "pass1")
        joined_group_id = create_test_group(client, "joined group").json()["id"]
        client.post(f"/api/groups/{joined_group_id}/progress", json={
            "start_page": 1,
            "end_page": 10,
        })

        # user1が参加していない別グループにも進捗を追加する。
        # この進捗がuser1のアクティビティに混ざらないことを確認する。
        signup_and_login(client, "user2", "pass2")
        other_group_id = create_test_group(client, "other group").json()["id"]
        client.post(f"/api/groups/{other_group_id}/progress", json={
            "start_page": 11,
            "end_page": 20,
        })

        # user1としてアクティビティを取得し、参加中グループの通常進捗だけが返ることを確認する。
        signup_and_login(client, "user1", "pass1")
        res = client.get("/api/groups/activities")

        assert res.status_code == 200
        activities = res.json()
        # 返るのはjoined groupに追加した1件だけ。
        # 初期進捗と未参加グループの進捗はどちらも含まれない。
        assert len(activities) == 1
        assert activities[0]["group_name"] == "joined group"
        # ホームの表示に不要なIDやページ情報を返していないことを確認する。
        assert set(activities[0].keys()) == {
            "group_name",
            "display_username",
            "display_time",
        }

    def test_activity_uses_you_for_current_user(self, client):
        """自分の進捗は表示用ユーザー名を「あなた」にする"""
        # user1が自分の参加グループに進捗を追加する。
        signup_and_login(client, "user1", "pass1")
        group_id = create_test_group(client, "my group").json()["id"]
        client.post(f"/api/groups/{group_id}/progress", json={
            "start_page": 1,
            "end_page": 10,
        })

        # 自分自身の進捗なので、画面表示用の名前は実ユーザー名ではなく「あなた」になる。
        res = client.get("/api/groups/activities")

        assert res.status_code == 200
        activity = res.json()[0]
        assert activity["display_username"] == "あなた"
        # 作成直後の進捗は、実行タイミングによって秒または分単位の表示になる。
        assert activity["display_time"].endswith(("秒前", "分前"))

    def test_activity_uses_username_for_other_member(self, client):
        """他メンバーの進捗は表示用ユーザー名に実ユーザー名を入れる"""
        # ownerがグループを作成する。
        signup_and_login(client, "owner", "pass")
        group_id = create_test_group(client, "member group").json()["id"]

        # memberが同じグループに参加し、進捗を追加する。
        signup_and_login(client, "member", "pass")
        client.post(f"/api/groups/{group_id}/join")
        client.post(f"/api/groups/{group_id}/progress", json={
            "start_page": 2,
            "end_page": 12,
        })

        # ownerから見ると他メンバーの進捗なので、表示名は「あなた」ではなくmemberになる。
        signup_and_login(client, "owner", "pass")
        res = client.get("/api/groups/activities")

        assert res.status_code == 200
        activity = res.json()[0]
        assert activity["display_username"] == "member"

    def test_activities_order_and_fixed_limit(self, client):
        """アクティビティは新しい順で、最大10件だけ返す"""
        # 最初にold groupへ進捗を追加し、古いアクティビティを作る。
        signup_and_login(client, "user1", "pass1")
        old_group_id = create_test_group(client, "old group").json()["id"]
        client.post(f"/api/groups/{old_group_id}/progress", json={
            "start_page": 1,
            "end_page": 1,
        })
        # 後から10件の進捗を追加し、old groupが固定表示件数の外へ押し出される状況を作る。
        for index in range(10):
            group_id = create_test_group(client, f"new group {index}").json()["id"]
            client.post(f"/api/groups/{group_id}/progress", json={
                "start_page": index + 2,
                "end_page": index + 2,
            })

        # URLでは件数を指定せず、バックエンド側の固定値である10件だけ取得する。
        res = client.get("/api/groups/activities")

        assert res.status_code == 200
        activities = res.json()
        assert len(activities) == 10
        # 最新順で返るため、最後に進捗を追加したグループが先頭になる。
        assert activities[0]["group_name"] == "new group 9"
        # 10件固定なので、古いold groupのアクティビティは返らない。
        assert all(activity["group_name"] != "old group" for activity in activities)
        assert activities[0]["display_time"].endswith(("秒前", "分前"))

    def test_format_activity_time(self):
        """経過時間に応じて、アクティビティ欄の表示形式を切り替える"""
        # 現在時刻に依存するとテスト結果が不安定になるため、基準時刻を固定する。
        now = datetime(2026, 5, 29, 12, 0, tzinfo=timezone.utc)

        # 経過時間の長さに応じて、秒・分・時間・日・日付表記へ切り替わることを確認する。
        assert format_activity_time(None, now) == "日時不明"
        assert format_activity_time(now - timedelta(seconds=30), now) == "30秒前"
        assert format_activity_time(now - timedelta(minutes=5), now) == "5分前"
        assert format_activity_time(now - timedelta(hours=3), now) == "3時間前"
        assert format_activity_time(now - timedelta(days=2), now) == "2日前"
        assert format_activity_time(now - timedelta(days=7), now) == "05/22"

class TestProgressFile:
    def test_upload_file(self, client):
        """グループメンバーはファイルをアップロードできる"""
        signup_and_login(client)
        group_id = create_test_group(client).json()["id"]
        progress_id = client.post(f"/api/groups/{group_id}/progress", json={
            "start_page": 1, "end_page": 50
        }).json()["id"]

        with open("app/test_code/upload_test.pdf", "rb") as f:
            res = client.post(
                f"/api/groups/{group_id}/progress/{progress_id}/upload",
                files={"file": ("upload_test.pdf", f, "application/pdf")}
            )
        assert res.status_code == 200
        assert res.json()["url"] is not None
        assert res.json()["file_type"] == "application/pdf"

    def test_upload_file_non_member(self, client):
        """グループメンバー以外はアップロードできない"""
        signup_and_login(client)
        group_id = create_test_group(client).json()["id"]
        progress_id = client.post(f"/api/groups/{group_id}/progress", json={
            "start_page": 1, "end_page": 50
        }).json()["id"]

        signup_and_login(client, "user2", "pass2")
        with open("app/test_code/upload_test.pdf", "rb") as f:
            res = client.post(
                f"/api/groups/{group_id}/progress/{progress_id}/upload",
                files={"file": ("upload_test.pdf", f, "application/pdf")}
            )
        assert res.status_code == 403

    def test_upload_file_invalid_progress(self, client):
        """存在しない進捗にはアップロードできない"""
        signup_and_login(client)
        group_id = create_test_group(client).json()["id"]

        with open("app/test_code/upload_test.pdf", "rb") as f:
            res = client.post(
                f"/api/groups/{group_id}/progress/999/upload",
                files={"file": ("upload_test.pdf", f, "application/pdf")}
            )
        assert res.status_code == 404

    def test_update_progress(self, client):
        """自分の進捗を編集できる"""
        signup_and_login(client)
        group_id = create_test_group(client).json()["id"]
        progress_id = client.post(f"/api/groups/{group_id}/progress", json={
            "start_page": 1, "end_page": 50
        }).json()["id"]
        res = client.patch(f"/api/groups/{group_id}/progress/{progress_id}", json={
            "start_page": 10, "end_page": 60, "memo": "修正しました"
        })
        assert res.status_code == 200
        assert res.json()["start_page"] == 10
        assert res.json()["end_page"] == 60
        assert res.json()["memo"] == "修正しました"

    def test_update_progress_by_owner(self, client):
        """オーナーは他のメンバーの進捗を編集できる"""
        signup_and_login(client)
        group_id = create_test_group(client).json()["id"]
        signup_and_login(client, "user2", "pass2")
        client.post(f"/api/groups/{group_id}/join")
        progress_id = client.post(f"/api/groups/{group_id}/progress", json={
            "start_page": 1, "end_page": 50
        }).json()["id"]
        signup_and_login(client)
        res = client.patch(f"/api/groups/{group_id}/progress/{progress_id}", json={
            "memo": "オーナーが修正"
        })
        assert res.status_code == 200

    def test_update_progress_by_non_owner(self, client):
        """他のメンバーの進捗は編集できない"""
        signup_and_login(client)
        group_id = create_test_group(client).json()["id"]
        progress_id = client.post(f"/api/groups/{group_id}/progress", json={
            "start_page": 1, "end_page": 50
        }).json()["id"]
        signup_and_login(client, "user2", "pass2")
        client.post(f"/api/groups/{group_id}/join")
        res = client.patch(f"/api/groups/{group_id}/progress/{progress_id}", json={
            "memo": "乗っ取り"
        })
        assert res.status_code == 403

    def test_delete_progress(self, client):
        """自分の進捗を削除できる"""
        signup_and_login(client)
        group_id = create_test_group(client).json()["id"]
        progress_id = client.post(f"/api/groups/{group_id}/progress", json={
            "start_page": 1, "end_page": 50
        }).json()["id"]
        res = client.delete(f"/api/groups/{group_id}/progress/{progress_id}")
        assert res.status_code == 200

    def test_delete_progress_by_non_owner(self, client):
        """他のメンバーの進捗は削除できない"""
        signup_and_login(client)
        group_id = create_test_group(client).json()["id"]
        progress_id = client.post(f"/api/groups/{group_id}/progress", json={
            "start_page": 1, "end_page": 50
        }).json()["id"]
        signup_and_login(client, "user2", "pass2")
        client.post(f"/api/groups/{group_id}/join")
        res = client.delete(f"/api/groups/{group_id}/progress/{progress_id}")
        assert res.status_code == 403

    def test_delete_group_by_owner(self, client):
        signup_and_login(client)
        group_id = create_test_group(client).json()["id"]
        res = client.delete(f"/api/groups/{group_id}")
        assert res.status_code == 200

    def test_delete_group_by_non_owner(self, client):
        signup_and_login(client)
        group_id = create_test_group(client).json()["id"]
        signup_and_login(client, "user2", "pass2")
        client.post(f"/api/groups/{group_id}/join")
        res = client.delete(f"/api/groups/{group_id}")
        assert res.status_code == 403
