from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from .. import database, crud, schemas
from ..dependencies import get_current_user_id

router = APIRouter(prefix="/api/recommend", tags=["recommend"])

@router.get("/", response_model=list[schemas.Recommend])
def get_recommend(
    db: Session = Depends(database.get_db)
):
    """
    おすすめの本を返すAPI。
    認証済みユーザーのみ利用可能。
    """
    return crud.get_recommend(db)

@router.post("/", response_model=schemas.Recommend)
def create_recommend(
    recommend: schemas.RecommendCreate,
    db: Session = Depends(database.get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    """
    おすすめの本を新規作成するAPI。
    認証済みユーザーのみ利用可能。
    """
    return crud.create_recommend(db=db, recommend=recommend)

@router.patch("/{recommend_id}", response_model=schemas.Recommend)
def update_recommend(
    recommend_id: int,
    is_active: bool = Query(..., description="このおすすめを表示するかどうか"),
    db: Session = Depends(database.get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    """
    おすすめの本の表示/非表示を切り替えるAPI。
    認証済みユーザーのみ利用可能。
    """
    updated = crud.update_recommend_active(db, recommend_id, is_active)
    if not updated:
        raise HTTPException(status_code=404, detail="Recommend not found")
    return updated
