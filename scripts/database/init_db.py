"""
Database initialization and session management.

Provides functions for:
- Creating database schema
- Getting database sessions
- Initializing with default data
"""

from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager

from .models import Base
from config import settings
from observability import get_logger

logger = get_logger(__name__)

# Global engine and session factory
_engine = None
_SessionFactory = None


def get_engine():
    """Get or create SQLAlchemy engine."""
    global _engine

    if _engine is None:
        # Create data directory if it doesn't exist
        db_path = Path(settings.database.path)
        db_path.parent.mkdir(parents=True, exist_ok=True)

        # Create engine
        database_url = f"sqlite:///{settings.database.path}"
        _engine = create_engine(
            database_url,
            echo=settings.database.echo,
            connect_args={'check_same_thread': False}  # Needed for SQLite
        )

        logger.info(f"Database engine created: {settings.database.path}")

    return _engine


def get_session_factory():
    """Get or create session factory."""
    global _SessionFactory

    if _SessionFactory is None:
        engine = get_engine()
        _SessionFactory = sessionmaker(bind=engine, expire_on_commit=False)

    return _SessionFactory


def get_session() -> Session:
    """
    Get a new database session.

    Returns:
        SQLAlchemy Session instance

    Example:
        session = get_session()
        try:
            # Use session
            ...
        finally:
            session.close()
    """
    SessionFactory = get_session_factory()
    return SessionFactory()


@contextmanager
def session_scope():
    """
    Context manager for database sessions.

    Automatically commits on success and rolls back on error.

    Yields:
        SQLAlchemy Session

    Example:
        with session_scope() as session:
            session.add(record)
            # Auto-commits on exit
    """
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_database(reset: bool = False):
    """
    Initialize the database schema.

    Creates all tables and optionally initializes default data.

    Args:
        reset: If True, drop all tables before creating (WARNING: DATA LOSS)

    Example:
        init_database()  # Create tables
        init_database(reset=True)  # Drop and recreate (development only)
    """
    engine = get_engine()

    if reset:
        logger.warning("Dropping all database tables (reset=True)")
        Base.metadata.drop_all(engine)

    # Create all tables
    Base.metadata.create_all(engine)
    logger.info("Database schema initialized")

    # Initialize default feature flags
    _initialize_default_flags()


def _initialize_default_flags():
    """Initialize default feature flags if they don't exist."""
    from .repository import AnalyticsRepository

    default_flags = [
        {
            'flag_name': 'cache_enabled',
            'enabled': True,
            'description': 'Enable Redis caching for LLM results'
        },
        {
            'flag_name': 'metrics_enabled',
            'enabled': True,
            'description': 'Enable metrics collection'
        },
        {
            'flag_name': 'consensus_enabled',
            'enabled': True,
            'description': 'Enable multi-LLM consensus analysis'
        },
        {
            'flag_name': 'admin_api_enabled',
            'enabled': True,
            'description': 'Enable admin API endpoints'
        },
    ]

    with session_scope() as session:
        repo = AnalyticsRepository(session)

        for flag_data in default_flags:
            existing = repo.get_feature_flag(flag_data['flag_name'])
            if not existing:
                repo.set_feature_flag(
                    flag_name=flag_data['flag_name'],
                    enabled=flag_data['enabled'],
                    description=flag_data['description']
                )
                logger.info(f"Initialized feature flag: {flag_data['flag_name']}")


def check_database_health() -> dict:
    """
    Check database health and return status.

    Returns:
        Dictionary with health status information
    """
    try:
        with session_scope() as session:
            # Try a simple query
            from .models import FeatureFlag
            count = session.query(FeatureFlag).count()

            return {
                'status': 'healthy',
                'database_path': settings.database.path,
                'feature_flags_count': count
            }

    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            'status': 'unhealthy',
            'error': str(e),
            'database_path': settings.database.path
        }
