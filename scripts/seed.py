from sqlalchemy import select

from backend.app.core.config import get_settings
from backend.app.core.security import hash_password
from backend.app.db.session import SessionLocal
from backend.app.models import User


def main() -> None:
    settings = get_settings()
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == settings.seed_email.lower()))
        if user is None:
            db.add(
                User(email=settings.seed_email.lower(), password_hash=hash_password(settings.seed_password))
            )
            db.commit()
            print("Researcher account created using .env credentials.")
        else:
            print("Researcher account already exists; password preserved.")


if __name__ == "__main__":
    main()
