from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt
from pwdlib import PasswordHash
from fastapi import Depends, Header, HTTPException

from database import get_db
from models import User
from settings import settings


def verify_password(plain_password: str, hashed_password: str) -> bool:
    ph = PasswordHash.recommended()
    return ph.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    ph = PasswordHash.recommended()
    return ph.hash(password)


def authenticate_user(db_session, email: str, password: str):
    user = db_session.query(User).filter(User.email == email).first()
    if not user:
        return False
    if not verify_password(password, user.password):
        return False
    return user


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.PASSWORD_HASH_ALGORITHM,
    )
    return encoded_jwt


def create_refresh_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=7)
    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.PASSWORD_HASH_ALGORITHM,
    )
    return encoded_jwt


def decode_token(token: str):
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.PASSWORD_HASH_ALGORITHM],
        )
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.PyJWTError:
        return None


def get_token(auth: str = Header(..., alias="Authorization")):
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    return auth[len("Bearer "):]


def auth_user(db_session=Depends(get_db), token: str = Depends(get_token)):

    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.PASSWORD_HASH_ALGORITHM],
        )

        id: str = payload.get("sub")
        if id is None:
            raise HTTPException(status_code=401, detail="Invalid token")

    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db_session.query(User).filter(User.id == UUID(id)).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user



def require_role(role: str):
    def role_checker(current_user: User = Depends(auth_user)):
        if current_user.role != role:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user

    return role_checker
