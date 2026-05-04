from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from .. import database, crud, schemas, auth_utils
from .. import dependencies

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
    db: Session = Depends(database.get_db),
    current_user_id: int = Depends(dependencies.get_current_user_id)
):
    """グループの進捗一覧を取得する。"""
    group = crud.get_group(db, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="グループが見つかりません")
    return crud.get_group_progresses(db, group_id)