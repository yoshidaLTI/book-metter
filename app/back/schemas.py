from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class ProgressBase(BaseModel):
    start_page: int
    end_page: int
    memo: Optional[str] = None

class ProgressCreate(ProgressBase):
    pass

class Progress(ProgressBase):
    id: int
    group_id: int
    user_id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class GroupBase(BaseModel):
    name: str
    owner: int
    is_lock: bool
    # 本の情報
    title: Optional[str] = None
    total_pages: Optional[int] = None
    author: Optional[str] = None
    publisher: Optional[str] = None
    published_date: Optional[str] = None
    description: Optional[str] = None
    self_link: Optional[str] = None
    api_id: Optional[str] = None
    api_etag: Optional[str] = None
    small_cover_url: Optional[str] = None
    cover_url: Optional[str] = None

class GroupCreate(GroupBase):
    password: str

class GroupUpdate(BaseModel):
    name: Optional[str] = None
    is_lock: Optional[bool] = None
    password: Optional[str] = None  # 変更する場合のみ


class Group(GroupBase):
    id: int
    progresses: List[Progress] = []
    members: List[User] = []

    class Config:
        from_attributes = True

class MembershipBase(BaseModel):
    pass

class GroupMemberCreate(MembershipBase):
    pass

class GroupMember(MembershipBase):
    group_id: int
    user_id: int

    class Config:
        from_attributes = True