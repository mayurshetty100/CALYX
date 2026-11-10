# ==============================================================================
# CALYX AUTH SERVICE: PYDANTIC DATA VALIDATION SCHEMAS
# ==============================================================================
# Concept Explanation for Beginners:
# Why do we need both SQLAlchemy Models and Pydantic Schemas?
# - SQLAlchemy Models represent the DATABASE state (tables, foreign keys).
# - Pydantic Schemas represent the NETWORK API state (incoming HTTP JSON requests
#   and outgoing HTTP JSON responses).
# Pydantic validates user input automatically. If a user submits an invalid email
# format or a password shorter than 8 characters, Pydantic immediately rejects it
# with a 422 Unprocessable Entity error BEFORE it ever touches your database!
# This protects against SQL injection and malformed payloads.
# ==============================================================================

from enum import Enum
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict


class UserRole(str, Enum):
    """
    Enumeration of allowed user roles within the CALYX ecosystem.
    """
    CANDIDATE = "candidate"  # Job seeker: can upload resumes, apply to jobs, view scores
    RECRUITER = "recruiter"  # Hiring manager: can post jobs, inspect candidate ranking
    ADMIN = "admin"          # System administrator: cluster management, audit oversight


class UserRegisterRequest(BaseModel):
    """
    Schema for incoming user registration HTTP request body.
    """
    # Validates standard RFC 5322 email syntax
    email: EmailStr = Field(..., description="Unique email address", json_schema_extra={"example": "candidate@calyx.ai"})

    # Enforces minimum 8-character password length for security
    password: str = Field(..., min_length=8, max_length=128, description="Plain text password (min 8 chars)", json_schema_extra={"example": "SecurePass123!"})

    # Full name of the user
    full_name: str = Field(..., min_length=2, max_length=100, description="Full name of the user", json_schema_extra={"example": "Ada Lovelace"})

    # Role must match one of the allowed enum values (defaults to candidate)
    role: UserRole = Field(default=UserRole.CANDIDATE, description="Role within CALYX platform")

    @field_validator("password")
    def validate_password_complexity(cls, v: str) -> str:
        """
        Defensive security check: password must contain at least one digit and one letter.
        """
        if not any(char.isdigit() for char in v):
            raise ValueError("Password must contain at least one numeric digit")
        if not any(char.isalpha() for char in v):
            raise ValueError("Password must contain at least one alphabetic character")
        return v


class UserLoginRequest(BaseModel):
    """
    Schema for incoming user login credentials.
    """
    email: EmailStr = Field(..., description="Registered account email", json_schema_extra={"example": "candidate@calyx.ai"})
    password: str = Field(..., description="Account password", json_schema_extra={"example": "SecurePass123!"})


class TokenRefreshRequest(BaseModel):
    """
    Schema for requesting a new short-lived access token using a long-lived refresh token.
    """
    refresh_token: str = Field(..., description="Valid issued refresh token string")


class UserResponse(BaseModel):
    """
    Schema for returning sanitized user profile data.
    Notice: `password_hash` is STRICTLY EXCLUDED to prevent credential leakage!
    """
    id: int = Field(..., description="Unique user identifier")
    email: EmailStr = Field(..., description="User's email address")
    full_name: str = Field(..., description="User's display name")
    role: str = Field(..., description="User's assigned role")
    is_active: bool = Field(..., description="Account active status")
    created_at: datetime = Field(..., description="Timestamp of account registration")

    # Tells Pydantic v2 to read attributes directly from SQLAlchemy ORM objects
    model_config = ConfigDict(from_attributes=True)


class AuthTokensData(BaseModel):
    """
    Payload containing both access and refresh tokens along with user profile.
    """
    access_token: str = Field(..., description="JWT bearer access token for authorization headers")
    refresh_token: str = Field(..., description="Long-lived token used to refresh access")
    token_type: str = Field(default="Bearer", description="HTTP Authorization header scheme")
    expires_in_seconds: int = Field(..., description="Lifespan of access token in seconds")
    user: UserResponse = Field(..., description="Sanitized user profile")


class TokenVerifyResponse(BaseModel):
    """
    Verification payload returned to internal microservices checking token validity.
    """
    valid: bool = Field(..., description="Whether the token is cryptographically valid and unexpired")
    user_id: Optional[int] = Field(default=None, description="Decoded user ID if valid")
    email: Optional[str] = Field(default=None, description="Decoded user email if valid")
    role: Optional[str] = Field(default=None, description="Decoded user role if valid")
