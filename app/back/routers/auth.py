from fastapi import APIRouter, Depends, HTTPException, Response, Cookie
from sqlalchemy.orm import Session
from .. import database, crud, schemas, auth_utils
from .. import dependencies
router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.post("/signup")
def signup(user: schemas.UserCreate, db: Session = Depends(database.get_db)):
    
    # 1. ユーザー名が既に使われていないかチェック
    existing_user = crud.get_user_by_username(db, username=user.username)
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")
        
    # 2. パスワードを暗号化
    hashed = auth_utils.hash_password(user.password)
    
    # 3. crud.py を呼び出す（引数の渡し方を crud.py に合わせる！）
    return crud.create_user(db=db, user=user, hashed_password=hashed)


@router.post("/login")
def login(user: schemas.UserCreate, response: Response, db: Session = Depends(database.get_db)):
    db_user = crud.get_user_by_username(db, username=user.username)
    
    if not db_user or not auth_utils.verify_password(user.password, db_user.password_hash):
        raise HTTPException(status_code=400, detail="ユーザー名かパスワードが違います")

    # セッションID（署名付き）を作成
    session_id = auth_utils.create_session_id(db_user.id)
    
    # Cookieをブラウザに保存させる
    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,   # JSからアクセス不可
        samesite="lax",  # CSRF対策
        max_age=60*60*24*3 # 3日間有効
    )
    return {"message": "ログインしました"}

@router.get("/me")
def get_me(
    user_id: int = Depends(dependencies.get_current_user_id), 
    db: Session = Depends(database.get_db)
):
    """
    現在のセッション(Cookie)が有効かチェックし、ユーザー情報を返します。
    無効なら get_current_user_id が 401 を投げます。
    """
    user = crud.get_user(db, user_id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"id": user.id, "username": user.username}

@router.post("/logout")
def logout(response: Response):
    # ブラウザに「session_idというCookieを削除してね」と命令する
    response.delete_cookie(key="session_id")
    return {"message": "ログアウトしました"}