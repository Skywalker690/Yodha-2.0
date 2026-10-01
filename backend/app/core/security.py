from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.db.session import get_db
from backend.app.models import User

hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return hasher.hash(password)


def verify_password(password: str, encoded: str) -> bool:
    try:
        return hasher.verify(encoded, password)
    except (VerifyMismatchError, VerificationError):
        return False


def create_token(user_id: str) -> str:
    settings = get_settings()
    return jwt.encode(
        {
            "sub": user_id,
            "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.token_minutes),
            "iat": datetime.now(timezone.utc),
            "iss": "neuropredict",
        },
        settings.jwt_secret,
        algorithm="HS256",
    )


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get("neuro_session", "")
    if request.headers.get("authorization", "").startswith("Bearer "):
        token = request.headers["authorization"][7:]
    try:
        payload = jwt.decode(
            token,
            get_settings().jwt_secret,
            algorithms=["HS256"],
            issuer="neuropredict",
            options={"require": ["exp", "sub", "iat"]},
        )
        user = db.get(User, payload["sub"])
        if user is None:
            raise ValueError("Unknown user")
        return user
    except (jwt.InvalidTokenError, ValueError):
        raise HTTPException(401, "Please sign in to continue.") from None
