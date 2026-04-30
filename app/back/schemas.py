from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

#=========================================#
# ユーザー（User）
#=========================================#
class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

#=========================================#
# 本（Book）
#=========================================#
class BookBase(BaseModel):
    title: str
    total_pages: int
    author: Optional[str] = None
    publisher: Optional[str] = None
    published_date: Optional[str] = None
    description: Optional[str] = None
    self_link: Optional[str] = None
    api_id: Optional[str] = None
    api_etag: Optional[str] = None
    small_cover_url: Optional[str] = None
    cover_url: Optional[str] = None

class BookCreate(BookBase):
    pass  # group_id は Group 側が持つので不要

class Book(BookBase):
    id: int

    class Config:
        from_attributes = True

#=========================================#
# 進捗ログ（Progress）← Group より先に定義
#=========================================#
class ProgressBase(BaseModel):
    start_page: int
    end_page: int
    memo: Optional[str] = None  # models.py に合わせて "memo" に統一

class ProgressCreate(ProgressBase):
    pass

class Progress(ProgressBase):
    id: int
    group_id: int
    user_id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

#=========================================#
# 輪講グループ（Group）
#=========================================#
class GroupBase(BaseModel):
    name: str
    owner: int
    is_lock: bool

class GroupCreate(GroupBase):
    password: str

class Group(GroupBase):
    id: int
    target_book: Optional[Book] = None   # None を許容
    progresses: List[Progress] = []
    members: List[User] = []

    class Config:
        from_attributes = True

#=========================================#
# メンバーシップ（Membership）
#=========================================#
class MembershipBase(BaseModel):
    pass

class GroupMemberCreate(MembershipBase):
    pass

class GroupMember(MembershipBase):
    group_id: int
    user_id: int

    class Config:
        from_attributes = True