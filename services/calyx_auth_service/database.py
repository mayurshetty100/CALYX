# ==============================================================================
# CALYX AUTH SERVICE: DATABASE CONNECTION & SESSION FACTORY
# ==============================================================================
# Concept Explanation for Beginners:
# 1. SQLAlchemy ORM (Object Relational Mapper):
#    Instead of writing raw SQL strings like "SELECT * FROM users WHERE email='...'",
#    an ORM allows us to interact with the database using Python objects and classes.
#
# 2. Connection Pooling:
#    Opening a new network socket to PostgreSQL on every single incoming web request
#    is slow and CPU-heavy. Connection pooling creates a pool of reusable database
#    connections. When a request arrives, it checks out an active connection, runs
#    queries, and checks it back into the pool.
#
# 3. Session Lifecycle & Dependency Injection:
#    In FastAPI, we use `get_db()` as a dependency generator (`yield`). It creates
#    an isolated database transaction for that request, and guarantees the session
#    is safely closed even if an unexpected error occurs.
# ==============================================================================

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from typing import Generator
from services.calyx_auth_service.config import auth_settings

# Determine if we are connecting to SQLite or PostgreSQL
# SQLite requires 'check_same_thread: False' to allow multi-threaded FastAPI workers
is_sqlite = auth_settings.DATABASE_URL.startswith("sqlite")
connect_args = {"check_same_thread": False} if is_sqlite else {}

# Create the SQLAlchemy Engine
# The engine is the central source of database connectivity
engine = create_engine(
    auth_settings.DATABASE_URL,
    connect_args=connect_args,
    # Pool size: number of permanent open connections to keep in the pool (for PostgreSQL)
    # Echo: set to False in production to avoid cluttering stdout with raw SQL statements
    echo=False
)

# Create a customized Sessionmaker class
# autocommit=False ensures transactions are explicitly committed
# autoflush=False prevents automatic flushing before queries unless specified
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# DeclarativeBase is the parent class from which all database models inherit
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that yields an independent database session per request.
    Automatically closes the session when the request processing finishes.
    """
    # Instantiate a fresh session from the connection pool
    db = SessionLocal()
    try:
        # Yield the session to the route handler
        yield db
    finally:
        # Guarantee session closure to prevent connection leaks
        db.close()
