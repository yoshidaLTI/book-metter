from fastapi import APIRouter, Depends, HTTPException, Response, Cookie
from sqlalchemy.orm import Session
from .. import database, crud, schemas, auth_utils
from .. import dependencies
router = APIRouter(prefix="/group", tags=["group"])

@router.get("/{group_id}/user")
# 一応認証なしでも閲覧可能
# そのグループに参加している全員の「名前とID」を取得
def get_group_users(group_id: int, db: Session = Depends(database.get_db)):
    group_users, user_id = crud.get_group_users(db, group_id)
    if group_users is None:
        raise HTTPException(status_code=404, detail="Group or users not found")
    return {"group_users": group_users, "user_id": user_id}

@router.post("/{group_id}/join")
# `is_lock: true` の場合はボディに `password` が必須。
def join_group(group_id: int, password: str = None, db: Session = Depends(database.get_db), current_user: schemas.User = Depends(dependencies.get_current_user)):
    success, message = crud.join_group(db, group_id, current_user.id, password)
    if not success:
        raise HTTPException(status_code=400, detail=message)
    return {"message": message}

@router.post("/{group_id}/leave")
# クッキーのユーザーが退会。オーナーの場合は退会不可（削除を促す）。
def leave_group(group_id: int, db: Session = Depends(database.get_db), current_user: schemas.User = Depends(dependencies.get_current_user)):
    success, message = crud.leave_group(db, group_id, current_user.id)
    if not success:
        raise HTTPException(status_code=400, detail=message)
    return {"message": message}


@router.get("/my-list")
# クッキーのユーザーが所属している「グループ名とID」を全取得。
def get_my_groups(db: Session = Depends(database.get_db), current_user: schemas.User = Depends(dependencies.get_current_user)):
    groups, group_ids = crud.get_user_groups(db, current_user.id)
    return {"groups": groups, "group_ids": group_ids}