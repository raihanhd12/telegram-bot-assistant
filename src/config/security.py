from datetime import datetime, timedelta
from typing import Optional

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader
from passlib.context import CryptContext
from starlette.status import HTTP_403_FORBIDDEN
from authlib.jose import jwt, JoseError

import src.config.env as env

# ================================
# 🔐 API KEY AUTHENTICATION
# ================================
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def validate_api_key(api_key: str = Security(api_key_header)):
    """
    Validate the API key if it's configured

    If no API key is configured in the settings, this is a no-op.
    Otherwise, it checks that the request contains a valid API key.
    """
    if env.API_KEY and env.API_KEY != "":
        if api_key != env.API_KEY:
            raise HTTPException(
                status_code=HTTP_403_FORBIDDEN, detail="Invalid API Key"
            )
    return api_key


# ================================
# 🔑 PASSWORD HASHING (Ready to use)
# ================================
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


# ================================
# 🎫 JWT TOKEN HANDLING (Ready to use)
# ================================
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """
    Create a JWT access token

    Args:
        data: The data to encode in the token
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        minutes = int(getattr(env, "ACCESS_TOKEN_EXPIRE_MINUTES", 15))
        expire = datetime.utcnow() + timedelta(minutes=minutes)

    to_encode.update({"exp": expire})
    secret_key = getattr(env, "SECRET_KEY", None)
    if not secret_key:
        raise RuntimeError("SECRET_KEY is not configured in src.config.env")
    algorithm = getattr(env, "ALGORITHM", "HS256")
    header = {"alg": algorithm}
    token = jwt.encode(header, to_encode, secret_key)
    return token


def verify_token(token: str) -> dict:
    """
    Verify and decode a JWT token

    Args:
        token: The JWT token to verify

    Returns:
        Decoded token payload

    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        secret_key = getattr(env, "SECRET_KEY", None)
        if not secret_key:
            raise RuntimeError("SECRET_KEY is not configured in src.config.env")
        data = jwt.decode(token, secret_key)
        return data
    except JoseError as exc:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN, detail="Could not validate credentials"
        ) from exc


# ================================
# 📋 USAGE EXAMPLES (Commented)
# ================================
#
# # Create a token
# token = create_access_token(data={"sub": "user123", "role": "user"})
#
# # Verify a token
# payload = verify_token(token)
# user_id = payload.get("sub")
#
# # Hash a password
# hashed = hash_password("mypassword")
#
# # Verify a password
# is_valid = verify_password("mypassword", hashed)
#
