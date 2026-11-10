# ==============================================================================
# CALYX AUTH SERVICE: RELATIONAL DATABASE MODELS (SQLAlchemy)
# ==============================================================================
# Concept Explanation for Beginners:
# Database Models are Python classes that map directly to physical database tables.
# Each attribute of the class corresponds to a column in that table.
# 1. Primary Key (`primary_key=True`): Unique identifier for each row (e.g. User ID 1, 2, 3).
# 2. Indexes (`index=True`): Like the index in the back of a textbook, an index allows
#    the database engine to locate a row (e.g. by email) in logarithmic time O(log N)
#    instead of scanning through millions of rows sequentially O(N).
# 3. Foreign Key (`ForeignKey`): Enforces referential integrity between tables.
#    A refresh token cannot exist without referencing a valid user!
# ==============================================================================

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from services.calyx_auth_service.database import Base


class User(Base):
    """
    SQLAlchemy model representing a registered user in CALYX.
    Can be a job candidate, a corporate recruiter, or a platform administrator.
    """
    # Name of the physical SQL table
    __tablename__ = "users"

    # Primary key: Unique numerical ID for each user
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # Email address: must be unique across all accounts and indexed for fast login lookups
    email = Column(String(255), unique=True, index=True, nullable=False)

    # Cryptographically hashed password (never plain text!)
    password_hash = Column(String(255), nullable=False)

    # User's display name or full legal name
    full_name = Column(String(255), nullable=False)

    # Role-Based Access Control (RBAC): 'candidate', 'recruiter', or 'admin'
    role = Column(String(50), default="candidate", index=True, nullable=False)

    # Soft deletion / account suspension flag: False if account is banned or deactivated
    is_active = Column(Boolean, default=True, nullable=False)

    # Timestamp when account was created in UTC
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Timestamp when user profile was last updated
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # One-to-many relationship: A user can have multiple refresh tokens across devices
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")


class RefreshToken(Base):
    """
    SQLAlchemy model storing issued refresh tokens for session rotation and revocation.
    """
    __tablename__ = "refresh_tokens"

    # Unique numerical identifier for the token record
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # Foreign key referencing the user who owns this token
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # SHA-256 hash of the refresh token string (stored as hash for defense-in-depth)
    token_hash = Column(String(255), unique=True, index=True, nullable=False)

    # Expiration datetime after which this token cannot be used
    expires_at = Column(DateTime, nullable=False)

    # Revocation flag: True if the user logged out or token was blacklisted
    revoked = Column(Boolean, default=False, nullable=False)

    # Timestamp when token was created
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationship back to the User model
    user = relationship("User", back_populates="refresh_tokens")


class AuditLog(Base):
    """
    SQLAlchemy model recording security events for auditing and intrusion detection.
    """
    __tablename__ = "audit_logs"

    # Unique log entry ID
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # Optional user ID associated with the action (can be None if login failed for unknown email)
    user_id = Column(Integer, nullable=True, index=True)

    # Machine-readable action code (e.g. 'USER_REGISTERED', 'LOGIN_SUCCESS', 'LOGIN_FAILED')
    action = Column(String(100), nullable=False, index=True)

    # IP address of the client that triggered the action
    ip_address = Column(String(50), nullable=True)

    # Extra diagnostic details or payload in text/JSON format
    details = Column(Text, nullable=True)

    # Timestamp of the audit event
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
