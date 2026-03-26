from fastapi import Cookie, HTTPException, Depends
from . import auth_utils

async def get_current_user_id(session_id: str = Cookie(None)):
    if not session_id:
        raise HTTPException(status_code=401, detail="ログインが必要です")
    
    user_id = auth_utils.get_user_id_from_session(session_id)
    if not user_id:
        raise HTTPException(status_code=401, detail="セッションが無効です")
    
    return user_id