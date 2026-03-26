from fastapi import FastAPI
from .database import engine
from . import models
# 💡 auth を追加
from .routers import users, books, auth 

# データベースのテーブル作成
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# --- ルーターの登録 ---

# 認証関連 (login, signup, /me など)
app.include_router(auth.router)

# ユーザー関連
app.include_router(users.router)

# 本・進捗関連
app.include_router(books.router) 

@app.get("/api/health")
def health_check():
    return {"status": "ok"}