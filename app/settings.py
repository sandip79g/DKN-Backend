from pathlib import Path

class Settings:
    BASE_DIR: Path = Path(__file__).resolve().parent.parent

    SECRET_KEY: str = "your_secret_key"

    DATABASE_URL: str = f"sqlite:///{BASE_DIR}/dkn_db.sqlite3"

    MEDIA_DIR: Path = BASE_DIR / "static" / "uploads"
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)

    PASSWORD_HASH_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

settings = Settings()
