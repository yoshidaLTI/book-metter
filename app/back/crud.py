from sqlalchemy.orm import Session
from . import models, schemas

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
# 2. 本の操作
# =================================================================

def get_books_by_group(db: Session, group_id: int):
    """グループに紐づく本を取得します。"""
    return db.query(models.Book).filter(models.Book.group_id == group_id).all()

def create_book(db: Session, book: schemas.BookCreate):
    db_book = models.Book(**book.model_dump())
    db.add(db_book)
    db.commit()
    db.refresh(db_book)
    return db_book

def delete_book(db: Session, book_id: int):
    db_book = db.query(models.Book).filter(models.Book.id == book_id).first()
    if db_book:
        db.delete(db_book)
        db.commit()
    return db_book

# =================================================================
# 3. グループ操作
# =================================================================

def get_group(db: Session, group_id: int):
    return db.query(models.Group).filter(models.Group.id == group_id).first()

def create_group(db: Session, group: schemas.GroupCreate, hashed_password: str):
    db_group = models.Group(
        name=group.name,
        owner=group.owner,
        is_lock=group.is_lock,
        password_hash=hashed_password
    )
    db.add(db_group)
    db.commit()
    db.refresh(db_group)
    return db_group

def join_group(db: Session, group_id: int, user_id: int, password: str = None):
    group = db.query(models.Group).filter(models.Group.id == group_id).first()
    if not group:
        return False, "グループが見つかりません"

    existing = db.query(models.Membership).filter_by(group_id=group_id, user_id=user_id).first()
    if existing:
        return False, "すでに参加しています"

    if group.is_lock and password != group.password_hash:
        return False, "パスワードが間違っています"

    db.add(models.Membership(group_id=group_id, user_id=user_id))
    db.commit()
    return True, "グループに参加しました"

def leave_group(db: Session, group_id: int, user_id: int):
    group = db.query(models.Group).filter(models.Group.id == group_id).first()
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
# 4. 進捗操作
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
    """重複・連続する読書範囲を統合し、実質的な総読了ページ数を算出します。"""
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