from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    books = relationship("Book", back_populates="owner")

class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    total_pages = Column(Integer)
    target_date = Column(String, nullable=True)

    # ▼ API (国立国会図書館) から取得する情報 ▼
    author = Column(String, nullable=True)         # 著者 (dc:creator)
    publisher = Column(String, nullable=True)      # 出版社 (dc:publisher) - 🌟追加
    published_year = Column(String, nullable=True) # 出版年 (dc:date)
    isbn = Column(String, nullable=True)           # ISBN (dc:identifier) - 🌟追加 (書影取得の鍵)
    description = Column(Text, nullable=True)      # 概要/説明 (description) - 🌟追加 (Text型で長文対応)
    ndl_link = Column(String, nullable=True)       # 国会図書館のリンク (link) - 🌟追加
    cover_url = Column(String, nullable=True)      # 書影画像URL (ISBNをもとにフロント側やAPI側で生成)

    # ▼ アプリ独自の管理情報 ▼
    status = Column(String, default="未読")         # ステータス（未読, 読書中, 読了）

    # タイムスタンプ
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="books")
    progress_logs = relationship("ProgressLog", back_populates="book")

class ProgressLog(Base):
    __tablename__ = "progress_logs"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(String)
    book_id = Column(Integer, ForeignKey("books.id"))

    start_page = Column(Integer)
    end_page = Column(Integer)
    memo = Column(Text, nullable=True) # メモも長くなる可能性があるのでText型がおすすめ

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    book = relationship("Book", back_populates="progress_logs")

# メモテーブル．ページ単位でのメモを管理するテーブル．
# group_idとuser_idは外部キーで管理する．locationはページ数や章番号などの位置情報を格納する．
class Memo(Base):
    __tablename__ = "memos"
    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("groups.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    location = Column(Integer)
    created = Column(DateTime(timezone=True), server_default=func.now())
    text = Column(Text)

# レジュメテーブル．輪講資料に関するテーブル．
# group_idとuser_idは外部キーで管理する．locationはページ数や章番号などの位置情報を格納する．
# URLはクラウド内の輪講資料の保存場所を示す．
class Resume(Base):
    __tablename__ = "resumes"
    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("groups.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    location = Column(Integer)
    created = Column(DateTime(timezone=True), server_default=func.now())
    url = Column(String)

# プロジェクトテーブル．輪講プロジェクトに関するテーブル．
# progress_id, memo_id, resume_idは外部キーで管理する．
class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True, index=True)
    progress_id = Column(Integer, ForeignKey("progress_logs.id"))
    memo_id = Column(Integer, ForeignKey("memos.id"))
    resume_id = Column(Integer, ForeignKey("resumes.id"))
