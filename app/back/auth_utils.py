from passlib.context import CryptContext
from itsdangerous import URLSafeSerializer
import os

# パスワードハッシュ化の設定
pwd_context = CryptContext(
    schemes=["pbkdf2_sha256"], # 👈 bcrypt の相性問題を避けるため pbkdf2 を使用
    deprecated="auto"
)

# Cookie署名用の鍵（本来は .env から取得）
SECRET_KEY = os.getenv("SECRET_KEY", "temporary-secret-key-12345")
serializer = URLSafeSerializer(SECRET_KEY)

def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)
    
def create_session_id(user_id: int):
    # user_id を署名付きの文字列に変換
    return serializer.dumps({"user_id": user_id})

def get_user_id_from_session(session_id: str):
    try:
        data = serializer.loads(session_id)
        return data.get("user_id")
    except:
        return None # 改ざんされていたり期限切れならNone