"""core/db/session.py: Database engine and session manager supporting SQLite and PostgreSQL."""

import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.pool import StaticPool
from core.db.models import Base

# Default to persistent local SQLite database file in data/aieval.db
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_SQLITE_URL = f"sqlite:///{DATA_DIR / 'aieval.db'}"

DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_SQLITE_URL)

# Configure engine
connect_args = {}
engine_kwargs = {"pool_pre_ping": True}

if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False, "timeout": 60.0}
    # pyrefly: ignore[bad-assignment]
    engine_kwargs["connect_args"] = connect_args
    if ":memory:" in DATABASE_URL:
        # pyrefly: ignore[bad-assignment]
        engine_kwargs["poolclass"] = StaticPool
else:
    # pyrefly: ignore[bad-assignment]
    engine_kwargs["pool_size"] = int(os.getenv("DB_POOL_SIZE", "10"))
    # pyrefly: ignore[bad-assignment]
    engine_kwargs["max_overflow"] = int(os.getenv("DB_MAX_OVERFLOW", "20"))

engine = create_engine(
    DATABASE_URL,
    **engine_kwargs,
)

# Enable SQLite WAL mode for high concurrency on file-backed databases
if DATABASE_URL.startswith("sqlite") and ":memory:" not in DATABASE_URL:
    with engine.connect() as conn:
        conn.exec_driver_sql("PRAGMA journal_mode=WAL;")
        conn.exec_driver_sql("PRAGMA synchronous=NORMAL;")

SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))


def init_db():
    """Initializes tables in database and applies lightweight non-destructive migrations."""
    Base.metadata.create_all(bind=engine)
    if DATABASE_URL.startswith("sqlite"):
        try:
            with engine.connect() as conn:
                res = conn.exec_driver_sql("PRAGMA table_info(trajectories);").fetchall()
                existing_cols = {row[1] for row in res}
                if existing_cols:
                    if "session_id" not in existing_cols:
                        conn.exec_driver_sql("ALTER TABLE trajectories ADD COLUMN session_id VARCHAR(128);")
                    if "sub_agents" not in existing_cols:
                        conn.exec_driver_sql("ALTER TABLE trajectories ADD COLUMN sub_agents JSON DEFAULT '[]';")
                conn.commit()
        except Exception:
            pass


def get_db():
    """Context manager / dependency for DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
