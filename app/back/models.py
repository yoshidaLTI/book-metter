from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base

# ============================== #
# 1. このファイル(models.py)の役割を大雑把に説明すると
# データベース（SQLiteやPostgreSQLなど）に作成するテーブルの構造を定義することが主な役割です。
# どんな名前の列（カラム）を作るか、どんなデータ型（数字？文字？）を保存するかを定義します。

# 2. schemas.py との違い
# - schemas.py: APIで「やり取り」するデータの形の定義（Pydanticモデル）。バリデーション担当。
# - models.py: データベースに「保存」するデータの形（SQLAlchemyモデル）。物理的な保存担当。

# 3. よく使われる用語の解説
# - primary_key=True: 「主キー」。データ1件1件を特定するための絶対に被らない背番号（ID）。
# - index=True: 検索を速くするための「索引（インデックス）」を作ります。
# - nullable=True: データベース上で「空っぽ（NULL）」を許す設定。schemasの Optional に相当します。
# - ForeignKey: 「外部キー」。他のテーブルのデータと紐づけるためのIDです。
# - relationship: Pythonのコード上で、紐づいたデータに簡単にアクセスするために使います。
# - func.now(): データベースの現在の時刻を自動で取得してくれます。created_atやupdated_atの自動記録に便利。
# ============================== #

#=========================================#
# ユーザー（User）のテーブル
#=========================================#
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True) # unique=True で同じ名前の登録を弾く
    password_hash = Column(String) # パスワードは暗号化（ハッシュ化）して保存します。
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    # user.books で「このユーザーが登録している本のリスト」にアクセスできるようにします。
    books = relationship("Book", back_populates="owner")

#=========================================#
# 本（Book）のテーブル設計図
#=========================================#
class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    total_pages = Column(Integer)
    target_date = Column(String, nullable=True)
    
    # ▼ API (国立国会図書館) から取得する情報 ▼
    author = Column(String, nullable=True)         # 著者 (dc:creator)
    publisher = Column(String, nullable=True)      # 出版社 (dc:publisher) 
    published_year = Column(String, nullable=True) # 出版年 (dc:date)
    isbn = Column(String, nullable=True)           # ISBN (dc:identifier) 
    description = Column(Text, nullable=True)      # 概要/説明 (description) 
    ndl_link = Column(String, nullable=True)       # 国会図書館のリンク (link)
    cover_url = Column(String, nullable=True)      # 書影画像URL (ISBNをもとにフロント側やAPI側で生成)

    # ▼ アプリ独自の管理情報 ▼
    status = Column(String, default="未読")         # ステータス（未読, 読書中, 読了）

    # タイムスタンプ
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
 
    # ▼ 他のテーブルとの紐づけ（リレーション） ▼
    # 「誰の本か？」を示すために、usersテーブルのidを外部キーとして保存します
    user_id = Column(Integer, ForeignKey("users.id"))
    # book.owner で「この本の持ち主（User）」にアクセスできるようにします。
    owner = relationship("User", back_populates="books")
    # book.progress_logs で「この本の進捗ログのリスト」にアクセスできるようにします。
    progress_logs = relationship("ProgressLog", back_populates="book")

#=========================================#
# 読書進捗ログ（ProgressLog）のテーブル設計図
#=========================================#
class Progress(Base):
    __tablename__ = "progresses"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("groups.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    progress_memo = Column(String)
    start_page = Column(Integer)
    end_page = Column(Integer)

    group = relationship("Group", back_populates="progresses")
    user = relationship("User", back_populates="progresses")

class Group(Base):
    __tablename__ = "groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    book_id = Column(Integer, ForeignKey("books.id"))

    target_book = relationship("Book", back_populates="groups")
    members = relationship("GroupMember", back_populates="group")
    progresses = relationship("Progress", back_populates="group")

class GroupMember(Base):
    __tablename__ = "group_members"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("groups.id"))
    user_id = Column(Integer, ForeignKey("users.id"))

    group = relationship("Group", back_populates="members")
    user = relationship("User", back_populates="joined_groups")