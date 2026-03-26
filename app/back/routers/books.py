from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from .. import crud, schemas, database, models
router = APIRouter(
    prefix="/api/books",
    tags=["books"]
)
from ..dependencies import get_current_user_id
# --- 本の一覧取得 ---

@router.get("/user/{user_id}", response_model=List[schemas.Book])
def read_user_books(user_id: int, db: Session = Depends(database.get_db)):
    """
    ① 本の一覧取得:
    特定のユーザーが登録している本をすべて取得します。
    各本には、重複を除いた既読ページ数（total_read_pages）が自動計算されて付与されます。
    """
    return crud.get_user_books(db, user_id=user_id)


# --- 本の新規登録 ---

@router.post("/", response_model=schemas.Book)
def create_book(book: schemas.BookCreate, db: Session = Depends(database.get_db),user_id: int = Depends(get_current_user_id)):
    """
    ② 本の新規登録:
    タイトル、総ページ数、目標日を設定して新しい本をリストに加えます。
    ※事前にユーザー登録（users router側）が完了している必要があります。
    """
    book.user_id = user_id # クッキーから判明した本人IDをセット
    return crud.create_user_book(db, book)


# --- 進捗の記録 ---

@router.post("/{book_id}/progress", response_model=schemas.Progress)
def create_progress(book_id: int, progress: schemas.ProgressCreate, db: Session = Depends(database.get_db)):
    """
    ③ 進捗の記録:
    読んだ範囲（開始〜終了ページ）を記録します。
    バリデーションにより、不正な数値（マイナスや本の最大ページ超え）はフロント側で弾かれますが、
    バックエンドでもデータの整合性をチェックします。
    """
    db_book = db.query(models.Book).filter(models.Book.id == book_id).first()
    if db_book is None:
        raise HTTPException(status_code=404, detail="記録対象の本が見つかりません。")
    return crud.create_book_progress(db=db, progress=progress, book_id=book_id)


# --- 本の削除 ---

@router.delete("/{book_id}")
def delete_book(book_id: int, db: Session = Depends(database.get_db)):
    """
    ④ 本の削除:
    本をリストから削除します。
    【注意】この操作を行うと、その本に紐づくすべての進捗ログも同時に削除されます。
    """
    db_book = crud.delete_book(db, book_id=book_id)
    if db_book is None:
        raise HTTPException(status_code=404, detail="削除対象の本が見つかりません。")
    return {"message": f"本 '{db_book.title}' を削除しました。"}