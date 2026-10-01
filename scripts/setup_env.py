"""Generate local-only credentials without overwriting an existing configuration."""

import secrets
from pathlib import Path


def main() -> None:
    path = Path(__file__).resolve().parents[1] / ".env"
    if path.exists():
        print("Existing .env preserved.")
        return
    password = secrets.token_urlsafe(24)
    path.write_text(
        f"POSTGRES_PASSWORD={password}\n"
        f"DATABASE_URL=postgresql+psycopg://neuropredict:{password}@127.0.0.1:5432/neuropredict\n"
        f"JWT_SECRET={secrets.token_urlsafe(48)}\n"
        "SEED_EMAIL=researcher@neuropredict.local\n"
        f"SEED_PASSWORD={secrets.token_urlsafe(18)}\n"
        "STORAGE_ROOT=storage\nDATASET_ROOT=dataset\n"
        "ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000\n",
        encoding="utf-8",
    )
    print("Created .env. Your local login is SEED_EMAIL / SEED_PASSWORD in that file.")


if __name__ == "__main__":
    main()
