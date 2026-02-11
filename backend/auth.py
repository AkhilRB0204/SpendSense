import re
import os
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from dotenv import load_dotenv

load_dotenv()

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

# Password hashing context
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)

# JWT Config
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("SECRET_KEY must be set in environment variables! Create a .env file with SECRET_KEY=your-secret-key")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# OAuth2 scheme for token extraction
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="users/login")

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
    global SECRET_KEY  # Add this line
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

# get current user from token
def get_current_user(token: str = Depends(oauth2_scheme)):
    """
    Extract and validate the current user from JWT token.
    Used as a dependency in protected routes.
    """
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = decode_access_token(token)
        if payload is None:
            raise credentials_exception
        
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        
        # Import here to avoid circular import
        from database import crud
        from database.database import SessionLocal
        
        db = SessionLocal()
        try:
            user = crud.get_user_by_email(db, email)
            if user is None:
                raise credentials_exception
            
            # Return user info as dict
            return {
                "user_id": user.user_id,
                "email": user.email,
                "name": user.name
            }
        finally:
            db.close()
            
    except JWTError:
        raise credentials_exception