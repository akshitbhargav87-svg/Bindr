from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from backend.app.core.config import settings

database_url = settings.DATABASE_URL
if database_url.startswith(("postgres://", "postgresql://")):
    database_url = "postgresql+psycopg://" + database_url.split("://", 1)[1]

connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
pool_options = {"pool_size": 5, "max_overflow": 0} if database_url.startswith("postgresql") else {}

engine = create_engine(
    database_url,
    connect_args=connect_args,
    **pool_options,
    pool_pre_ping=True,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def run_sqlite_migrations(db_engine):
    """
    Safely migrates existing SQLite databases without destructive schema changes.
    Checks tables and adds missing columns such as cases.owner_id.
    """
    if db_engine.dialect.name != "sqlite":
        return
    try:
        from sqlalchemy import inspect, text
        inspector = inspect(db_engine)
        tables = inspector.get_table_names()
        if "cases" in tables:
            columns = [col["name"] for col in inspector.get_columns("cases")]
            additions = {
                "owner_id": "VARCHAR(100) NOT NULL DEFAULT 'legacy-unclaimed'",
                "version": "INTEGER NOT NULL DEFAULT 1",
                "resolution_note": "TEXT",
                "resolved_at": "VARCHAR(50)",
            }
            with db_engine.begin() as conn:
                for name, definition in additions.items():
                    if name not in columns:
                        conn.execute(text(f"ALTER TABLE cases ADD COLUMN {name} {definition}"))
    except Exception as e:
        import logging
        logging.getLogger("backend.app.core.database").exception("Database migration failed")
        raise


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
