from fastapi import APIRouter, Depends, HTTPException, Query ,UploadFile, File
from sqlalchemy.orm import Session
from .. import database, crud, schemas, auth_utils ,models
from .. import dependencies
from mimetypes import guess_type

import os
import uuid

router = APIRouter(prefix="/api/groups", tags=["groups"])


@router.post("/", response_model=schemas.Group)
def create_group(
    group: schemas.GroupCreate,
    db: Session = Depends(database.get_db),
    current_user_id: int = Depends(dependencies.get_current_user_id)
):
    """グループを新規作成する。ownerは自動でログイン中のユーザーになる。"""
    hashed = auth_utils.hash_password(group.password)
    return crud.create_group(db=db, group=group, hashed_password=hashed)


@router.get("/", response_model=list[schemas.Group])
def get_all_groups(
    db: Session = Depends(database.get_db),
    current_user_id: int = Depends(dependencies.get_current_user_id)
):
    """全グループを取得する（グループ検索画面用）。"""
    return crud.get_all_groups(db)



@router.get("/my-list", response_model=list[schemas.Group])
def get_my_groups(
    db: Session = Depends(database.get_db),
    current_user_id: int = Depends(dependencies.get_current_user_id)
):
    """ログイン中のユーザーが所属しているグループ一覧を取得する。"""
    return crud.get_user_groups(db, current_user_id)

@router.get("/search/by-name", response_model=list[schemas.Group])
def search_by_name(
    q: str = Query(..., description="グループ名の検索キーワード"),
    db: Session = Depends(database.get_db),
    current_user_id: int = Depends(dependencies.get_current_user_id)
):
    """グループ名で検索する。"""
    results = crud.search_groups_by_name(db, q)
    if not results:
        raise HTTPException(status_code=404, detail="該当するグループが見つかりません")
    return results


@router.get("/search/by-book", response_model=list[schemas.Group])
def search_by_book(
    q: str = Query(..., description="本のタイトルの検索キーワード"),
    db: Session = Depends(database.get_db),
    current_user_id: int = Depends(dependencies.get_current_user_id)
):
    """課題図書のタイトルで検索する。"""
    results = crud.search_groups_by_book(db, q)
    if not results:
        raise HTTPException(status_code=404, detail="該当するグループが見つかりません")
    return results


@router.delete("/{group_id}")
def delete_group(
    group_id: int,
    db: Session = Depends(database.get_db),
    current_user_id: int = Depends(dependencies.get_current_user_id)
):
    """グループを削除する。オーナーのみ可能。"""
    group = crud.get_group(db, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="グループが見つかりません")
    if group.owner != current_user_id:
        raise HTTPException(status_code=403, detail="オーナーのみ削除できます")
    crud.delete_group(db, group_id)
    return {"message": "グループを削除しました"}

@router.patch("/{group_id}", response_model=schemas.Group)
def update_group(
    group_id: int,
    update_data: schemas.GroupUpdate,
    db: Session = Depends(database.get_db),
    current_user_id: int = Depends(dependencies.get_current_user_id)
):
    """グループ設定を更新する。オーナーのみ可能。"""
    group = crud.get_group(db, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="グループが見つかりません")
    if group.owner != current_user_id:
        raise HTTPException(status_code=403, detail="オーナーのみ設定を変更できます")
    
    hashed = auth_utils.hash_password(update_data.password) if update_data.password else None
    updated = crud.update_group(db, group_id, update_data, hashed)
    return updated


@router.get("/{group_id}", response_model=schemas.Group)
def get_group(
    group_id: int,
    db: Session = Depends(database.get_db),
    current_user_id: int = Depends(dependencies.get_current_user_id)
):
    """指定したグループの詳細を取得する。"""
    group = crud.get_group(db, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="グループが見つかりません")
    if not crud.is_group_member(db, group_id, current_user_id):
        raise HTTPException(status_code=403, detail="グループメンバーのみ閲覧できます")
    return group

@router.post("/{group_id}/join")
def join_group(
    group_id: int,
    password: str = Query(None),
    db: Session = Depends(database.get_db),
    current_user_id: int = Depends(dependencies.get_current_user_id)
):
    """グループに参加する。is_lock=true の場合は password が必要。"""
    success, message = crud.join_group(db, group_id, current_user_id, password)
    if not success:
        raise HTTPException(status_code=400, detail=message)
    return {"message": message}


@router.post("/{group_id}/leave")
def leave_group(
    group_id: int,
    db: Session = Depends(database.get_db),
    current_user_id: int = Depends(dependencies.get_current_user_id)
):
    """グループから退会する。オーナーは退会不可。"""
    success, message = crud.leave_group(db, group_id, current_user_id)
    if not success:
        raise HTTPException(status_code=400, detail=message)
    return {"message": message}


@router.post("/{group_id}/progress", response_model=schemas.Progress)
def create_progress(
    group_id: int,
    progress: schemas.ProgressCreate,
    db: Session = Depends(database.get_db),
    current_user_id: int = Depends(dependencies.get_current_user_id)
):
    """進捗を記録する。"""
    group = crud.get_group(db, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="グループが見つかりません")
    return crud.create_progress(db, progress, group_id, current_user_id)


@router.get("/{group_id}/progress", response_model=list[schemas.Progress])
def get_progresses(
    group_id: int,
    limit: int = Query(None),  
    db: Session = Depends(database.get_db),
    current_user_id: int = Depends(dependencies.get_current_user_id)
):
    group = crud.get_group(db, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="グループが見つかりません")
    return crud.get_group_progresses(db, group_id, limit=limit)


@router.patch("/{group_id}/progress/{progress_id}", response_model=schemas.Progress)
def update_progress(
    group_id: int,
    progress_id: int,
    update_data: schemas.ProgressUpdate,
    db: Session = Depends(database.get_db),
    current_user_id: int = Depends(dependencies.get_current_user_id)
):
    """進捗を編集する。自分の進捗またはオーナーのみ可能。"""
    group = crud.get_group(db, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="グループが見つかりません")

    progress = db.query(models.Progress).filter(models.Progress.id == progress_id).first()
    if not progress:
        raise HTTPException(status_code=404, detail="進捗が見つかりません")

    if progress.user_id != current_user_id and group.owner != current_user_id:
        raise HTTPException(status_code=403, detail="編集権限がありません")

    return crud.update_progress(db, progress_id, update_data)


@router.delete("/{group_id}/progress/{progress_id}")
def delete_progress(
    group_id: int,
    progress_id: int,
    db: Session = Depends(database.get_db),
    current_user_id: int = Depends(dependencies.get_current_user_id)
):
    """進捗を削除する。自分の進捗またはオーナーのみ可能。"""
    group = crud.get_group(db, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="グループが見つかりません")

    progress = db.query(models.Progress).filter(models.Progress.id == progress_id).first()
    if not progress:
        raise HTTPException(status_code=404, detail="進捗が見つかりません")

    if progress.user_id != current_user_id and group.owner != current_user_id:
        raise HTTPException(status_code=403, detail="削除権限がありません")

    crud.delete_progress(db, progress_id)
    return {"message": "削除しました"}

#~=================================================================
#　ファイルアップロードのためのエンドポイント
#~=================================================================
UPLOAD_DIR = "/app/uploads"

@router.post("/{group_id}/progress/{progress_id}/upload", response_model=schemas.Progress)
async def upload_progress_file(
    group_id: int,
    progress_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(database.get_db),
    current_user_id: int = Depends(dependencies.get_current_user_id)
):
    """進捗にファイルを添付する。グループメンバーであれば誰でも可能。"""
    group = crud.get_group(db, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="グループが見つかりません")

    progress = db.query(models.Progress).filter(models.Progress.id == progress_id).first()
    if not progress:
        raise HTTPException(status_code=404, detail="進捗が見つかりません")
    
    # グループメンバーかチェック
    if not crud.is_group_member(db, group_id, current_user_id):
        raise HTTPException(status_code=403, detail="グループメンバーのみアップロードできます")

    os.makedirs(UPLOAD_DIR, exist_ok=True)


    os.makedirs(UPLOAD_DIR, exist_ok=True)

    ext = os.path.splitext(file.filename)[1]
    filename = f"{uuid.uuid4()}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)

    mime_type, encoding = guess_type(filename)
    if not mime_type:
        mime_type = file.content_type or "application/octet-stream"

    with open(filepath, "wb") as f:
        content = await file.read()
        f.write(content)

    progress.url = f"/uploads/{filename}"
    progress.file_type = file.content_type
    db.commit()
    db.refresh(progress)

    return progress
