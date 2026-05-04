from fastapi import FastAPI
from .database import engine
from . import models
from .routers import auth, group, books

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

app.include_router(auth.router)
app.include_router(group.router)
app.include_router(books.router)  # Google Books検索用

@app.get("/api/health")
def health_check():
    return {"status": "ok"}