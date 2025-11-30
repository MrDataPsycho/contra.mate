"""
PostgreSQL database setup and session management for SQLModel.

Provides synchronous engine, session factory, and database initialization utilities.
"""

from contextlib import contextmanager
from typing import Generator, Optional

from loguru import logger
from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, Session
from sqlmodel import SQLModel

from contramate.utils.settings.core import PostgresSettings


class PostgreSQLDatabase:
    """
    PostgreSQL database manager with synchronous support.

    Handles engine creation, session management, and table creation.
    """

    def __init__(self, settings: PostgresSettings):
        """
        Initialize database with settings.

        Args:
            settings: PostgreSQL settings with connection parameters
        """
        self.settings = settings
        self._engine: Optional[Engine] = None
        self._session_factory: Optional[sessionmaker] = None

    @property
    def engine(self) -> Engine:
        """Get or create engine"""
        if self._engine is None:
            # Use the same connection string and engine config as other services
            connection_string = self.settings.connection_string
            self._engine = create_engine(connection_string, echo=False)
            logger.info(f"Created engine for database: {self.settings.database}")

        return self._engine

    @property
    def session_factory(self) -> sessionmaker:
        """Get or create session factory"""
        if self._session_factory is None:
            self._session_factory = sessionmaker(
                self.engine,
                class_=Session,
                expire_on_commit=False,
            )
            logger.info("Created session factory")

        return self._session_factory

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        Get database session as context manager.

        Usage:
            with db.get_session() as session:
                # Use session here
                pass
        """
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Session error: {e}")
            raise
        finally:
            session.close()

    def create_tables(self):
        """
        Create all SQLModel tables.

        Should be called once during application startup or migration.
        """
        from contramate.dbs.models import Conversation, Message

        SQLModel.metadata.create_all(self.engine)
        logger.info("Created all database tables")

    def drop_tables(self):
        """
        Drop all SQLModel tables.

        WARNING: This will delete all data! Use only in development/testing.
        """
        from contramate.dbs.models import Conversation, Message

        SQLModel.metadata.drop_all(self.engine)
        logger.warning("Dropped all database tables")

    def close(self):
        """Close database connections"""
        if self._engine:
            self._engine.dispose()
            logger.info("Closed database engine")


# Global database instance (initialized in FastAPI lifespan)
_db_instance: Optional[PostgreSQLDatabase] = None


def init_db(settings: PostgresSettings) -> PostgreSQLDatabase:
    """
    Initialize global database instance.

    Args:
        settings: PostgreSQL settings

    Returns:
        PostgreSQL database instance
    """
    global _db_instance
    _db_instance = PostgreSQLDatabase(settings)
    logger.info("Initialized PostgreSQL database")
    return _db_instance


def get_db() -> PostgreSQLDatabase:
    """
    Get global database instance.

    Returns:
        PostgreSQL database instance

    Raises:
        RuntimeError: If database not initialized
    """
    if _db_instance is None:
        raise RuntimeError(
            "Database not initialized. Call init_db() first in your application startup."
        )
    return _db_instance


def get_session() -> Generator[Session, None, None]:
    """
    FastAPI dependency for getting database session.

    Usage in FastAPI:
        @app.get("/items")
        def get_items(session: Session = Depends(get_session)):
            # Use session here
            pass
    """
    db = get_db()
    with db.get_session() as session:
        yield session
