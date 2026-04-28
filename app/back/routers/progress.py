from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from .. import database, models, schemas, dependencies

# ============================== #
# 1. このファイル(progress.py)の役割
# 読書進捗（Progress）に関するAPIエンドポイントを定義します。
# ユーザーが読んだページ数を記録したり、グループ内での進捗を確認したりするための機能を提供します。
# ============================== #

router = APIRouter(prefix="/api/progress", tags=["progress"])

# 1. 進捗の取得: GET /group/{group_id}/progress
@router.get("/group/{group_id}/progress", response_model=List[schemas.Progress])
def get_progress(
    group_id: int,
    mine: bool = Query(False),
    db: Session = Depends(database.get_db),
    current_user_id: int = Depends(dependencies.get_current_user_id)
):
    query = db.query(models.Progress).filter(models.Progress.group_id == group_id)
    if mine:
        query = query.filter(models.Progress.user_id == current_user_id)
    return query.all()

# 2. 進捗を記録: POST /group/{group_id}/progress
@router.post("/group/{group_id}/progress", response_model=schemas.Progress)
def create_progress(
    group_id: int,
    progress_in: schemas.ProgressCreate,
    db: Session = Depends(database.get_db),
    current_user_id: int = Depends(dependencies.get_current_user_id)
):
    db_progress = models.Progress(
        **progress_in.model_dump(),
        group_id=group_id,
        user_id=current_user_id
    )
    db.add(db_progress)
    db.commit()
    db.refresh(db_progress)
    return db_progress

# 3. 進捗を修正: PATCH /group/progress/{progress_id}
@router.patch("/group/progress/{progress_id}", response_model=schemas.Progress)
def update_progress(
    progress_id: int,
    progress_in: schemas.ProgressBase, 
    db: Session = Depends(database.get_db),
    current_user_id: int = Depends(dependencies.get_current_user_id)
):
    db_progress = db.query(models.Progress).filter(
        models.Progress.id == progress_id,
        models.Progress.user_id == current_user_id
    ).first()
    
    if not db_progress:
        raise HTTPException(
            status_code=403, 
            detail="指定された進捗データが見つからないか、編集権限がありません"
        )

    update_data = progress_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_progress, field, value)
    
    db.commit()
    db.refresh(db_progress)
    return db_progress

# 4. 進捗を削除: DELETE /group/progress/{progress_id}
@router.delete("/group/progress/{progress_id}")
def delete_progress(
    progress_id: int,
    db: Session = Depends(database.get_db),
    current_user_id: int = Depends(dependencies.get_current_user_id)
):
    db_progress = db.query(models.Progress).filter(
        models.Progress.id == progress_id,
        models.Progress.user_id == current_user_id
    ).first()

    if not db_progress:
        raise HTTPException(
            status_code=403, 
            detail="指定された進捗データが見つからないか、削除権限がありません"
        )

    db.delete(db_progress)
    db.commit()
    return {"message": "削除完了"}
