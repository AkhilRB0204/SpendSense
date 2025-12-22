import re
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException

def validate_email(email: str):
    """
    Very basic email validation: must contain '@' and '.'
    """
    if not email or "@" not in email or "." not in email:
        raise HTTPException(status_code=400, detail="Invalid email format")

def validate_password(password: str):
    """
    Validate password strength:
    - At least 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character
    """
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters long")
    if not re.search(r"[A-Z]", password):
        raise HTTPException(status_code=400, detail="Password must contain at least one uppercase letter")
    if not re.search(r"[a-z]", password):
        raise HTTPException(status_code=400, detail="Password must contain at least one lowercase letter")
    if not re.search(r"\d", password):
        raise HTTPException(status_code=400, detail="Password must contain at least one digit")
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>_/-]", password):
        raise HTTPException(status_code=400, detail="Password must contain at least one special character")
    return True

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
    return pwd_context.verify(plain_password, hashed_password)

# create access token
def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM
    )

    return encoded_jwt

# decode access token
def decode_access_token(token: str) -> dict | None:
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