# ==============================================================================
# CALYX AUTH SERVICE: BUSINESS LOGIC SERVICE LAYER
# ==============================================================================
# Concept Explanation for Beginners:
# The "Service Layer" pattern isolates business rules away from the web framework
# (FastAPI) and the database (SQLAlchemy).
# Why is this good engineering?
# 1. Testability: You can test registration, login, and token rotation directly
#    without spinning up HTTP servers or sending web requests.
# 2. Maintainability: If tomorrow we switch from FastAPI to gRPC, our business
#    logic remains 100% untouched and reusable!
# ==============================================================================

import hashlib
from datetime import datetime, timezone, timedelta
from typing import Tuple, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from common.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_and_verify_token,
)
from services.calyx_auth_service.models import User, RefreshToken, AuditLog
from services.calyx_auth_service.schemas import UserRegisterRequest, AuthTokensData, UserResponse
from services.calyx_auth_service.config import auth_settings


class AuthService:
    """
    Core business logic for identity management, authentication, and token lifecycles.
    """

    @staticmethod
    def _hash_token_string(token: str) -> str:
        """
        Creates a SHA-256 digest of a token string before storing it in the database.
        Defense-in-depth: if database is ever breached, attackers cannot use leaked
        refresh tokens directly.
        """
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @staticmethod
    def _create_audit_entry(
        db: Session,
        action: str,
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        details: Optional[str] = None
    ) -> None:
        """
        Helper method to record an immutable audit event in the database.
        """
        audit_entry = AuditLog(
            user_id=user_id,
            action=action,
            ip_address=ip_address,
            details=details
        )
        db.add(audit_entry)
        db.commit()

    @classmethod
    def register(cls, db: Session, req: UserRegisterRequest, ip_address: Optional[str] = None) -> User:
        """
        Registers a new user account with hashed password and initial audit log.
        Raises HTTP 409 Conflict if email is already taken.
        """
        # Step 1: Check if an account already exists with this email
        existing_user = db.query(User).filter(User.email == req.email.lower().strip()).first()
        if existing_user:
            cls._create_audit_entry(
                db,
                action="REGISTRATION_FAILED_EMAIL_CONFLICT",
                ip_address=ip_address,
                details=f"Email collision attempt for: {req.email}"
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"An account with email '{req.email}' already exists."
            )

        # Step 2: Hash the plain-text password using salted bcrypt
        hashed_pw = hash_password(req.password)

        # Step 3: Create and persist the new User entity
        new_user = User(
            email=req.email.lower().strip(),
            password_hash=hashed_pw,
            full_name=req.full_name.strip(),
            role=req.role.value,
            is_active=True
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        # Step 4: Write audit log
        cls._create_audit_entry(
            db,
            action="USER_REGISTERED_SUCCESSFULLY",
            user_id=new_user.id,
            ip_address=ip_address,
            details=f"Role: {new_user.role}"
        )

        return new_user

    @classmethod
    def authenticate_and_generate_tokens(
        cls,
        db: Session,
        email: str,
        plain_password: str,
        ip_address: Optional[str] = None
    ) -> AuthTokensData:
        """
        Validates credentials and issues an Access Token (short-lived) + Refresh Token (long-lived).
        Raises HTTP 401 Unauthorized if email or password do not match.
        """
        # Step 1: Retrieve user by email
        user = db.query(User).filter(User.email == email.lower().strip()).first()
        
        # Step 2: Verify user exists and password hash matches
        if not user or not verify_password(plain_password, user.password_hash):
            cls._create_audit_entry(
                db,
                action="LOGIN_FAILED_INVALID_CREDENTIALS",
                user_id=user.id if user else None,
                ip_address=ip_address,
                details=f"Failed login attempt for email: {email}"
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password."
            )

        # Step 3: Verify that account is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This account has been deactivated. Please contact support."
            )

        # Step 4: Generate short-lived JWT Access Token
        access_token_expires = timedelta(minutes=auth_settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            subject=str(user.id),
            role=user.role,
            secret_key=auth_settings.JWT_SECRET_KEY,
            algorithm=auth_settings.JWT_ALGORITHM,
            expires_delta=access_token_expires,
            extra_claims={"email": user.email, "full_name": user.full_name}
        )

        # Step 5: Generate long-lived Refresh Token
        refresh_token = create_refresh_token(
            subject=str(user.id),
            secret_key=auth_settings.JWT_SECRET_KEY,
            algorithm=auth_settings.JWT_ALGORITHM,
            expires_days=auth_settings.REFRESH_TOKEN_EXPIRE_DAYS
        )

        # Step 6: Store hashed refresh token in database for rotation & revocation tracking
        token_hash = cls._hash_token_string(refresh_token)
        refresh_record = RefreshToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(days=auth_settings.REFRESH_TOKEN_EXPIRE_DAYS),
            revoked=False
        )
        db.add(refresh_record)
        db.commit()

        # Step 7: Log audit event
        cls._create_audit_entry(
            db,
            action="LOGIN_SUCCESSFUL",
            user_id=user.id,
            ip_address=ip_address,
            details=f"Token issued for user ID {user.id}"
        )

        return AuthTokensData(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="Bearer",
            expires_in_seconds=auth_settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=UserResponse.model_validate(user)
        )

    @classmethod
    def refresh_access_token(
        cls,
        db: Session,
        refresh_token_str: str,
        ip_address: Optional[str] = None
    ) -> AuthTokensData:
        """
        Validates an existing refresh token and issues a new access token.
        """
        # Step 1: Cryptographically verify token signature and expiration
        try:
            payload = decode_and_verify_token(
                refresh_token_str,
                secret_key=auth_settings.JWT_SECRET_KEY,
                algorithm=auth_settings.JWT_ALGORITHM
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid or expired refresh token: {str(e)}"
            )

        if payload.get("token_type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Supplied token is not a refresh token."
            )

        user_id = int(payload.get("sub"))

        # Step 2: Verify in database that this refresh token has not been revoked
        token_hash = cls._hash_token_string(refresh_token_str)
        token_record = db.query(RefreshToken).filter(
            RefreshToken.token_hash == token_hash,
            RefreshToken.user_id == user_id,
            RefreshToken.revoked == False
        ).first()

        if not token_record:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has been revoked or does not exist."
            )

        # Step 3: Fetch active user record
        user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User associated with token no longer exists or is disabled."
            )

        # Step 4: Generate fresh access token
        access_token_expires = timedelta(minutes=auth_settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        new_access_token = create_access_token(
            subject=str(user.id),
            role=user.role,
            secret_key=auth_settings.JWT_SECRET_KEY,
            algorithm=auth_settings.JWT_ALGORITHM,
            expires_delta=access_token_expires,
            extra_claims={"email": user.email, "full_name": user.full_name}
        )

        cls._create_audit_entry(
            db,
            action="ACCESS_TOKEN_REFRESHED",
            user_id=user.id,
            ip_address=ip_address
        )

        return AuthTokensData(
            access_token=new_access_token,
            refresh_token=refresh_token_str,
            token_type="Bearer",
            expires_in_seconds=auth_settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=UserResponse.model_validate(user)
        )
