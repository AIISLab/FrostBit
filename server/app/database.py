from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from .models import Base

BASE_DIR = Path(__file__).resolve().parent

SQLALCHEMY_DATABASE_URL = f"sqlite:///{BASE_DIR / 'frost.db'}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},  # needed for SQLite + FastAPI
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Call this once on startup (or import it in main.py)
def init_db() -> None:
    Base.metadata.create_all(bind=engine)
