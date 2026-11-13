"""
Database connection and session management for PostgreSQL using SQLAlchemy.
"""
import logging
from contextlib import contextmanager
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from core.config import DATABASE_URL

logger = logging.getLogger(__name__)

# SQLAlchemy Base class for models
Base = declarative_base()

engine = None
SessionLocal = None
_engine_error = None

def get_engine():
    """Lazily creates and returns the SQLAlchemy engine."""
    global engine, SessionLocal, _engine_error
    if engine is None:
        try:
            connect_args = {}
            if "postgresql" in DATABASE_URL:
                connect_args = {"connect_timeout": 2}
            engine = create_engine(
                DATABASE_URL,
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True,
                echo=False,
                connect_args=connect_args,
            )
            SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=engine,
                expire_on_commit=False
            )
            _engine_error = None
        except Exception as e:
            _engine_error = str(e)
            logger.error(f"Failed to create database engine: {e}")
            raise
    return engine

@contextmanager
def get_db():
    """Context manager for database sessions with automatic commit/rollback and close."""
    get_engine()
    if SessionLocal is None:
        raise RuntimeError(f"Database session not available: {_engine_error}")
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Database session rollback due to: {e}")
        raise
    finally:
        db.close()

def check_connection() -> tuple[bool, str]:
    """
    Tests the connection to the PostgreSQL database.
    Returns (success: bool, message: str)
    """
    try:
        eng = get_engine()
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, "Connected to PostgreSQL successfully"
    except Exception as e:
        return False, str(e)

def init_db():
    """Creates all tables registered in Base metadata if they don't exist."""
    from core import models_db  # Ensure models are imported before creating tables
    eng = get_engine()
    Base.metadata.create_all(bind=eng)

    # Ensure file_hash column exists in PostgreSQL
    try:
        with eng.connect() as conn:
            conn.execute(text("ALTER TABLE training_images ADD COLUMN IF NOT EXISTS file_hash VARCHAR(64);"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_training_images_file_hash ON training_images(file_hash);"))
            conn.commit()
    except Exception as e:
        logger.warning(f"Note on DB schema sync: {e}")
