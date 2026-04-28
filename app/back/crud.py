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