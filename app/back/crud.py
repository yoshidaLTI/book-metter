from sqlalchemy.orm import Session
from . import models, schemas
from typing import Optional
from .auth_utils import verify_password
from datetime import datetime, timezone

# =================================================================
# 1. ユーザー操作
# =================================================================

def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()

def create_user(db: Session, user: schemas.UserCreate, hashed_password: str):
    db_user = models.User(
        username=user.username,
        password_hash=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# =================================================================
# 2. グループ操作
# =================================================================

def get_group(db: Session, group_id: int):
    return db.query(models.Group).filter(models.Group.id == group_id).first()

def search_groups_by_name(db: Session, keyword: str):
    """グループ名で部分一致検索"""
    return db.query(models.Group).filter(
        models.Group.name.contains(keyword)
    ).all()

def search_groups_by_book(db: Session, keyword: str):
    """本のタイトルで部分一致検索"""
    return db.query(models.Group).filter(
        models.Group.title.contains(keyword)
    ).all()

def get_all_groups(db: Session):
    return db.query(models.Group).all()

def create_group(db: Session, group: schemas.GroupCreate, hashed_password: str):
    db_group = models.Group(
        name=group.name,
        owner=group.owner,
        is_lock=group.is_lock,
        password_hash=hashed_password,
        title=group.title,
        total_pages=group.total_pages,
        author=group.author,
        publisher=group.publisher,
        published_date=group.published_date,
        description=group.description,
        self_link=group.self_link,
        api_id=group.api_id,
        api_etag=group.api_etag,
        small_cover_url=group.small_cover_url,
        cover_url=group.cover_url,
    )
    db.add(db_group)
    db.flush()

    # オーナーを membership に自動追加
    membership = models.Membership(group_id=db_group.id, user_id=group.owner)
    db.add(membership)
    
    # Progressのmemoとして「ownerがグループを作成しました」
    # が出力されるように変更
    owner_user = get_user(db, group.owner)
    initial_memo = (
        f"{owner_user.username} がグループを作成しました"
        if owner_user
        else "グループを作成しました"
    )

    # 読書量には含めない初期進捗を追加することで
    # グループ作成後に作成したグループを先頭に表示する
    initial_progress = models.Progress(
        group_id=db_group.id,
        user_id=group.owner,
        start_page=0,
        end_page=0,
        memo=initial_memo
    )
    db.add(initial_progress)

    db.commit()
    db.refresh(db_group)

    return db_group
def update_group_book(db: Session, group_id: int, book_data: schemas.GroupBase):
    """グループの課題図書情報を更新する"""
    db_group = get_group(db, group_id)
    if not db_group:
        return None
    db_group.title = book_data.title
    db_group.total_pages = book_data.total_pages
    db_group.author = book_data.author
    db_group.publisher = book_data.publisher
    db_group.published_date = book_data.published_date
    db_group.description = book_data.description
    db_group.self_link = book_data.self_link
    db_group.api_id = book_data.api_id
    db_group.api_etag = book_data.api_etag
    db_group.small_cover_url = book_data.small_cover_url
    db_group.cover_url = book_data.cover_url
    db.commit()
    db.refresh(db_group)
    return db_group

def update_group(db: Session, group_id: int, update_data: schemas.GroupUpdate, hashed_password: Optional[str] = None):
    """グループ設定を更新する"""
    group = get_group(db, group_id)
    if not group:
        return None
    if update_data.name is not None:
        group.name = update_data.name
    if update_data.is_lock is not None:
        group.is_lock = update_data.is_lock
    if hashed_password is not None:
        group.password_hash = hashed_password
    db.commit()
    db.refresh(group)
    return group


def join_group(db: Session, group_id: int, user_id: int, password: str = None):
    group = get_group(db, group_id)
    if not group:
        return False, "グループが見つかりません"
    existing = db.query(models.Membership).filter_by(group_id=group_id, user_id=user_id).first()
    if existing:
        return False, "すでに参加しています"
    if group.is_lock:
        if not password:
            return False, "パスワードが必要です"
        if not verify_password(password, group.password_hash):  # ← ハッシュで比較
            return False, "パスワードが間違っています"
    db.add(models.Membership(group_id=group_id, user_id=user_id))
    db.commit()
    return True, "グループに参加しました"

def leave_group(db: Session, group_id: int, user_id: int):
    group = get_group(db, group_id)
    if not group:
        return False, "グループが見つかりません"
    if group.owner == user_id:
        return False, "オーナーは退会できません。グループを削除してください。"
    member = db.query(models.Membership).filter_by(group_id=group_id, user_id=user_id).first()
    if not member:
        return False, "グループに参加していません"
    db.delete(member)
    db.commit()
    return True, "グループから退会しました"

def get_user_groups(db: Session, user_id: int):
    memberships = db.query(models.Membership).filter_by(user_id=user_id).all()
    return [m.group for m in memberships]

def is_group_member(db: Session, group_id: int, user_id: int) -> bool:
    return db.query(models.Membership).filter_by(
        group_id=group_id, user_id=user_id
    ).first() is not None

def delete_group(db: Session, group_id: int):
    group = db.query(models.Group).filter(models.Group.id == group_id).first()
    if not group:
        return False
    db.delete(group)
    db.commit()
    return True
# =================================================================
# 3. 進捗操作
# =================================================================

def create_progress(db: Session, progress: schemas.ProgressCreate, group_id: int, user_id: int):
    db_progress = models.Progress(
        **progress.model_dump(),
        group_id=group_id,
        user_id=user_id
    )
    db.add(db_progress)
    db.commit()
    db.refresh(db_progress)
    return db_progress


def get_group_progresses(db: Session, group_id: int, limit: int = None):
    query = db.query(models.Progress)\
        .filter(models.Progress.group_id == group_id)\
        .order_by(models.Progress.id.desc())
    if limit:
        query = query.limit(limit)
    return query.all()

def format_activity_time(created_at: datetime, now: datetime) -> str:
    """アクティビティ欄に表示する経過時間の文字列を作成する。"""
    if created_at is None:
        return "日時不明"

    # タイムゾーンが設定されていない場合は、比較用にUTCとして扱う。
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)

    # Progressの作成時刻と現在時刻の差から、表示用の経過時間を作る。
    elapsed_seconds = max(0, int((now - created_at).total_seconds()))
    elapsed_minutes = elapsed_seconds // 60
    elapsed_hours = elapsed_minutes // 60
    elapsed_days = elapsed_hours // 24

    if elapsed_seconds < 60:
        return f"{elapsed_seconds}秒前"
    if elapsed_minutes < 60:
        return f"{elapsed_minutes}分前"
    if elapsed_hours < 24:
        return f"{elapsed_hours}時間前"
    if elapsed_days < 7:
        return f"{elapsed_days}日前"
    return created_at.strftime("%m/%d")

def get_user_progress_activities(db: Session, user_id: int):
    """
    ホーム画面のアクティビティ欄に出す最新進捗を組み立てる。

    例: 「田中 が 5分前に A班 へ進捗を追加しました」
    のように表示できるよう、DBから参加中グループの進捗を取り出し、
    フロントがそのまま使える表示用データへ整える。
    """
    rows = (
        db.query(models.Progress, models.User, models.Group)
        .join(models.User, models.Progress.user_id == models.User.id)
        .join(models.Group, models.Progress.group_id == models.Group.id)
        .join(
            models.Membership,
            models.Membership.group_id == models.Progress.group_id
        )
        # Membership.user_idで所属グループを絞るため、同じグループ内の他メンバーの進捗も残る。
        .filter(models.Membership.user_id == user_id)
        # グループ作成時の初期進捗は、実際の進捗追加ではないため除外する。
        .filter(models.Progress.start_page > 0)
        .filter(models.Progress.end_page >= models.Progress.start_page)
        .order_by(models.Progress.id.desc())
        # ホーム画面には最新10件だけを表示する。
        .limit(10)
        .all()
    )

    now = datetime.now(timezone.utc)
    activities = []
    for progress, user, group in rows:
        activities.append({
            "group_name": group.name,
            "display_username": "あなた" if user.id == user_id else user.username,
            "display_time": format_activity_time(progress.created_at, now),
        })

    return activities

def update_progress(db: Session, progress_id: int, update_data: schemas.ProgressUpdate):
    progress = db.query(models.Progress).filter(models.Progress.id == progress_id).first()
    if not progress:
        return None
    if update_data.start_page is not None:
        progress.start_page = update_data.start_page
    if update_data.end_page is not None:
        progress.end_page = update_data.end_page
    if update_data.memo is not None:
        progress.memo = update_data.memo
    db.commit()
    db.refresh(progress)
    return progress

def delete_progress(db: Session, progress_id: int):
    progress = db.query(models.Progress).filter(models.Progress.id == progress_id).first()
    if not progress:
        return False
    db.delete(progress)
    db.commit()
    return True


def calculate_total_progress(logs):
    if not logs:
        return 0
    intervals = sorted(
        (log.start_page, log.end_page)
        for log in logs
        if log.start_page > 0 and log.end_page >= log.start_page
        # start_pageが0以上であることを条件に追加することで
        # グループ作成時に自動的に追加するinitial_progress(start_page=end_page=0)
        # を読んだ合計ページ数として計算させないようにする
    )
    if not intervals:
        return 0
    merged = []
    for start, end in intervals:
        if not merged or start > merged[-1][1] + 1:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)
    return sum(end - start + 1 for start, end in merged)

# =================================================================
# 4. おすすめの本
# =================================================================
# おすすめの本を取得する（is_active=Trueのものだけ）
def get_recommend(db: Session):
    return db.query(models.Recommend).filter_by(is_active=True).all()

# おすすめの本を作成する
def create_recommend(db: Session, recommend: schemas.RecommendCreate):
    db_recommend = models.Recommend(**recommend.model_dump())
    db.add(db_recommend)
    db.commit()
    db.refresh(db_recommend)
    return db_recommend

# おすすめの本を削除する
def update_recommend_active(db: Session, recommend_id: int, is_active: bool):
    recommend = db.query(models.Recommend).filter(models.Recommend.id == recommend_id).first()
    if not recommend:
        return None
    recommend.is_active = is_active
    db.commit()
    db.refresh(recommend)
    return recommend
