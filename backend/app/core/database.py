from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from backend.app.core.config import settings

connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def run_sqlite_migrations(db_engine):
    """
    Safely migrates existing SQLite databases without destructive schema changes.
    Checks tables and adds missing columns such as cases.owner_id.
    """
    try:
        from sqlalchemy import inspect, text
        inspector = inspect(db_engine)
        tables = inspector.get_table_names()
        if "cases" in tables:
            columns = [col["name"] for col in inspector.get_columns("cases")]
            if "owner_id" not in columns:
                with db_engine.begin() as conn:
                    conn.execute(text("ALTER TABLE cases ADD COLUMN owner_id VARCHAR(100) NOT NULL DEFAULT 'demo-user'"))
    except Exception as e:
        import logging
        logging.getLogger("backend.app.core.database").warning(f"Database migration check failed or skipped: {e}")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
