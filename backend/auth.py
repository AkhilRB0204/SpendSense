from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext

# Password hasing context
pwd_context = CryptContext (
    schemes=["bcrypt"],
    deprecated="auto"
)

# JWT config
SECRET_KEY = "your_secret_key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# hashing password
def hash_password(password: str) -> str:
    """Hash a plaintext password."""
    return pwd_context.hash(password)


# password verification
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plaintext password against hashed password"""
    return pwd_context.verify_password(plain_password, hashed_password)

# create access token
def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(ACCESS_TOKEN_EXPIRE_MINUTES)
        )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM
    )

    return encoded_jwt

# decode access token
def decode_access_token(token: str):
    """
    Decode & validate JWT token
    """
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )
        return payload
    except JWTError:
        return None