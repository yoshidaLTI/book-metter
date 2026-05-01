from fastapi import APIRouter, Depends, HTTPException, Response, Cookie
from sqlalchemy.orm import Session
from .. import database, crud, schemas, auth_utils
from .. import dependencies
router = APIRouter(prefix="/group", tags=["group"])

@router.post("/", response_model=schemas.Group)
def create_group(
    group_data: schemas.GroupCreate,
    db: Session = Depends(database.get_db),
    user_id: int = Depends(get_current_user_id)
):
    """
    グループ作成: 
    フロントエンドから送られてきた「本の情報」と「グループ情報」をDBに保存します。
    """
    # 1. グループ名の重複チェック
    existing_group = db.query(models.Group).filter(models.Group.name == group_data.name).first()
    if existing_group:
        raise HTTPException(status_code=400, detail="このグループ名は既に使用されています")
    # 2. パスワードロックがある場合は暗号化
    if group_data.is_lock and group_data.password:
        group_data.password = auth_utils.hash_password(group_data.password)
    # 3. CRUDを呼び出して、本・グループ・メンバーを一気に保存
    created_group = crud.create_group_with_book(db=db, group_data=group_data, user_id=user_id
    return created_group

@router.get("/search", response_model=list[schemas.GroupBasic])
def search_groups(q: str, db: Session = Depends(database.get_db)):
    """本の名前でグループを検索します"""
    groups = crud.search_groups_by_book(db, q)
    return groups

@router.delete("/{group_id}")
def delete_group(group_id: int, db: Session = Depends(database.get_db), current_user: schemas.User = Depends(dependencies.get_current_user)):
    """グループ削除（オーナーのみ）"""
    success, message = crud.delete_group(db, group_id, current_user.id)
    if not success:
        raise HTTPException(status_code=403, detail=message)
    return {"message": message}


@router.get("/{group_id}")
def get_group(group_id: int, db: Session = Depends(database.get_db), current_user: schemas.User = Depends(dependencies.get_current_user)):
    """
    グループ情報取得
    参加者orオーナーなら詳細（本・進捗・レジュメ）を取得。未参加なら基本情報のみ。
    """
    group, is_member = crud.get_group_info(db, group_id, current_user.id)
    
    if not group:
        raise HTTPException(status_code=404, detail="グループが見つかりません")

    if is_member:
        # 詳細情報を返す (schemas.GroupDetail で設定した形に変換して返す)
        # ※ルーターで分岐して返す型を変えるため、今回は response_model は使わず直で返すか、
        # Pydanticモデルに変換してから返します。
        return schemas.GroupDetail.model_validate(group)
    else:
        # 基本情報のみを返す
        return schemas.GroupBasic.model_validate(group)


@router.patch("/{group_id}/settings")
def update_group_settings(
    group_id: int, 
    settings: schemas.GroupSettingsUpdate, 
    db: Session = Depends(database.get_db), 
    current_user: schemas.User = Depends(dependencies.get_current_user)
):
    """設定変更（オーナーのみ）"""
    success, message = crud.update_group_settings(db, group_id, current_user.id, settings)
    if not success:
        raise HTTPException(status_code=403, detail=message)
    return {"message": message}

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
