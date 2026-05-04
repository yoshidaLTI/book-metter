from sqlalchemy.orm import Session
from . import models, schemas
from typing import Optional
from .auth_utils import verify_password

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

def get_group_progresses(db: Session, group_id: int):
    return db.query(models.Progress).filter(models.Progress.group_id == group_id).all()

def calculate_total_progress(logs):
    if not logs:
        return 0
    intervals = sorted([(log.start_page, log.end_page) for log in logs])
    merged = []
    for start, end in intervals:
        if not merged or start > merged[-1][1] + 1:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)
    return sum(end - start + 1 for start, end in merged)