# Gestion de sesiones SQLAlchemy 2 (SQLite en desarrollo/CI, MySQL 8 en Docker/RDS)
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from src.db.config import obtener_configuracion
from src.db.models import Base


def create_engine_from_url(url: str | None = None):
    db_url = url or obtener_configuracion().database_url
    kwargs = {"future": True, "pool_pre_ping": True}
    if db_url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    engine = create_engine(db_url, **kwargs)

    if db_url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def _activar_fk(dbapi_connection, _connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


def create_session_factory(url: str | None = None):
    engine = create_engine_from_url(url)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False), engine


def init_db(url: str | None = None):
    engine = create_engine_from_url(url)
    Base.metadata.create_all(bind=engine)
    return engine


def get_db():
    session_factory, _ = create_session_factory()
    db = session_factory()
    try:
        yield db
    finally:
        db.close()
