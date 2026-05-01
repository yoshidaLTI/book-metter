from sqlalchemy.orm import Session
from . import models, schemas

# =================================================================
# 1. ユーザー操作 (User Operations)
# =================================================================

def get_user(db: Session, user_id: int):
    """IDでユーザーを検索します。主にAPIの認証や存在確認で使用します。"""
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_user_by_username(db: Session, username: str):
    """ユーザー名で検索します。ログイン時の重複チェックなどに利用します。"""
    return db.query(models.User).filter(models.User.username == username).first()

def create_user(db: Session, user: schemas.UserCreate, hashed_password: str):
    """
    新規ユーザーを作成します。
    auth.py で安全にハッシュ化（暗号化）されたパスワードを受け取って保存します。
    """
    # ユーザー名と、暗号化済みのパスワードをDBにセットする
    db_user = models.User(
        username=user.username, 
        password_hash=hashed_password  
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# =================================================================
# 2. 本の操作 (Book Operations)
# =================================================================

def get_user_books(db: Session, user_id: int):
    """特定のユーザーが所有する全ての本を取得します。"""
    return db.query(models.Book).filter(models.Book.user_id == user_id).all()

def create_user_book(db: Session, book: schemas.BookCreate):
    """ユーザーに関連付けて新しい本を登録します。"""
    db_book = models.Book(
        title=book.title,
        total_pages=book.total_pages,
        target_date=book.target_date,
        user_id=book.user_id
    )
    db.add(db_book)
    db.commit()
    db.refresh(db_book)
    return db_book

def delete_book(db: Session, book_id: int):
    """
    本を削除します。
    DB側のCASCADE設定により、紐づくProgressLogも自動的に削除されます。
    """
    db_book = db.query(models.Book).filter(models.Book.id == book_id).first()
    if db_book:
        db.delete(db_book)
        db.commit()
    return db_book

# =================================================================
# 3. 進捗計算ロジック (Progress Calculation)
# =================================================================

def create_book_progress(db: Session, progress: schemas.ProgressCreate, book_id: int):
    """特定のページ範囲の読書記録を保存します。"""
    db_progress = models.ProgressLog(
        **progress.model_dump(),
        book_id=book_id
    )
    db.add(db_progress)
    db.commit()
    db.refresh(db_progress)
    return db_progress

def calculate_total_progress(logs):
    """
    【コアロジック】重複・連続する読書範囲を統合し、実質的な総読了ページ数を算出します。
    
    アルゴリズムの仕組み:
    1. 全てのログを開始ページ順にソート。
    2. 前の範囲の終わりと、今の範囲の始まりが重なっている、または連続(+1)していれば統合。
    3. 統合された各ブロックの長さを合計。
    
    例: [[1, 10], [11, 20], [50, 60]] -> 統合結果: [[1, 20], [50, 60]] -> 合計: 31ページ
    """
    if not logs:
        return 0
    
    # 1. 開始ページでソートして処理を効率化
    intervals = sorted([(log.start_page, log.end_page) for log in logs])
    
    # 2. 重複範囲をマージ (Merge Overlapping Intervals)
    merged = []
    for start, end in intervals:
        # 初回、または現在の開始位置が「前の終了位置 + 1」より後ろなら、新しい区間として追加
        if not merged or start > merged[-1][1] + 1: 
            merged.append([start, end])
        else:
            # 重なっている、または「10ページ」の次に「11ページ」が来ている場合は末尾を更新
            merged[-1][1] = max(merged[-1][1], end)
            
    # 3. 各区間のページ数を算出 (終了 - 開始 + 1) して合計
    total = sum(end - start + 1 for start, end in merged)
    return total

# =================================================================
# 4. グループ操作 (Group Operations)
# =================================================================

def create_group_with_book(db: Session, group_data: schemas.GroupCreate, user_id: int):
    """【追加】本とグループを同時に作成し、作成者をオーナー兼メンバーとして登録します"""
    # 1. まず本を保存
    db_book = models.Book(**group_data.book.model_dump())
    db.add(db_book)
    db.commit()
    db.refresh(db_book)

    # 2. グループを保存
    db_group = models.Group(
        name=group_data.name,
        book_id=db_book.id,
        owner_id=user_id,
        is_lock=group_data.is_lock,
        password=group_data.password
    )
    db.add(db_group)
    db.commit()
    db.refresh(db_group)

    # 3. オーナーを初期メンバーとして登録
    new_member = models.GroupMember(group_id=db_group.id, user_id=user_id)
    db.add(new_member)
    db.commit()

    return db_group

def get_group_users(db: Session, group_id: int):
    # 特定のグループに所属するユーザーを取得します。
    # グループ取得
    group = db.query(models.Group).filter(models.Group.id == group_id).first()
    if not group:
        return None, None
    # グループメンバーからユーザIDを抽出
    user_ids = [member.user_id for member in group.members]
    return group.members, user_ids


def join_group(db: Session, group_id: int, user_id: int, password: str = None):
    # グループにユーザーを参加させる
    group = db.query(models.Group).filter(models.Group.id == group_id).first()
    if not group:
        return False, "グループが見つかりません"
    
    # 参加前の重複チェック
    existing_member = db.query(models.GroupMember).filter_by(group_id=group_id, user_id=user_id).first()
    if existing_member:
        return False, "すでに参加しています"
    
    # パスワードが必要な場合の検証
    if group.is_lock and password != group.password:
        return False, "パスワードが間違っています"
    
    # グループメンバーシップを作成
    new_member = models.GroupMember(group_id=group_id, user_id=user_id)
    db.add(new_member)
    db.commit()
    return True, "グループに参加しました"

def leave_group(db: Session, group_id: int, user_id: int):
    # グループからユーザーを退会させる
    group = db.query(models.Group).filter(models.Group.id == group_id).first()
    if not group:
        return False, "グループが見つかりません"
    
    # 退会前の存在チェック
    member = db.query(models.GroupMember).filter_by(group_id=group_id, user_id=user_id).first()
    if not member:
        return False, "グループに参加していません"
    
    # オーナーが退会しようとした場合の処理
    if group.owner_id == user_id:
        return False, "オーナーは退会できません。グループを削除してください。"
    
    # グループメンバーシップを削除
    db.delete(member)
    db.commit()
    return True, "グループから退会しました"

def get_user_groups(db: Session, user_id: int):
    # ユーザーが所属しているグループを取得します。
    memberships = db.query(models.GroupMember).filter_by(user_id=user_id).all()
    groups = [membership.group.name for membership in memberships]
    ids = [membership.group_id for membership in memberships]
    return groups, ids

def delete_group(db: Session, group_id: int, user_id: int):
    """グループを削除します（オーナーのみ）"""
    group = db.query(models.Group).filter(models.Group.id == group_id).first()
    if not group:
        return False, "グループが見つかりません"

    if group.owner_id != user_id:
        return False, "グループを削除する権限がありません"

    # グループと紐づく本を取得して削除
    book = db.query(models.Book).filter(models.Book.id == group.book_id).first()
    db.delete(group)
    if book:
        db.delete(book)

    db.commit()
    return True, "グループを削除しました"


def get_group_info(db: Session, group_id: int, user_id: int = None):
    """グループ情報を取得し、リクエストした人が参加者かどうかの判定も返します"""
    group = db.query(models.Group).filter(models.Group.id == group_id).first()
    if not group:
        return None, False

    is_member = False
    if user_id:
        if group.owner_id == user_id:
            is_member = True
        else:
            member = db.query(models.GroupMember).filter_by(group_id=group_id, user_id=user_id).first()
            if member:
                is_member = True

    return group, is_member


def update_group_settings(db: Session, group_id: int, user_id: int, settings: schemas.GroupSettingsUpdate):
    """グループの設定と本の情報を更新します（オーナーのみ）"""
    group = db.query(models.Group).filter(models.Group.id == group_id).first()
    if not group:
        return False, "グループが見つかりません"

    if group.owner_id != user_id:
        return False, "設定を変更する権限がありません"

    # Noneでない（変更希望が送られてきた）項目だけを上書き
    if settings.is_lock is not None:
        group.is_lock = settings.is_lock
    if settings.password is not None:
        group.password = settings.password

    if settings.book:
        book = db.query(models.Book).filter(models.Book.id == group.book_id).first()
        if book:
            # Pydanticの機能を使って、未送信の項目(None)を無視して辞書化
            update_data = settings.book.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                setattr(book, key, value)

    db.commit()
    return True, "設定を更新しました"


def search_groups_by_book(db: Session, book_name: str):
    """本の名前でグループを検索します（部分一致）"""
    groups = db.query(models.Group).join(models.Book).filter(
        models.Book.title.ilike(f"%{book_name}%")
    ).all()
    return groups
