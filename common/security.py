# ==============================================================================
# CALYX COMMON MODULE: SECURITY, CRYPTOGRAPHY & JWT AUTHENTICATION
# ==============================================================================
# Concept Explanation for Beginners:
# 1. Password Hashing:
#    Never store passwords in plain text! Even if a hacker dumps your database,
#    they should only see a salted one-way mathematical hash. We use 'bcrypt',
#    an algorithm that incorporates a random "salt" and deliberately takes CPU cycles
#    to compute, making offline brute-force attacks computationally infeasible.
#
# 2. JSON Web Tokens (JWT):
#    In a microservices architecture, having every microservice constantly query the
#    Auth database to verify "Is this user logged in?" creates a massive bottleneck.
#    Instead, when a user logs in, the Auth service signs a digital passport called
#    a JWT. The JWT contains claims (like user_id, role, expiry) and a cryptographic
#    signature. Downstream services can verify this signature independently using
#    only the shared secret key—zero database queries required!
# ==============================================================================

import time
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import jwt
import bcrypt


def hash_password(plain_password: str) -> str:
    """
    Takes a plain-text password and returns its salted bcrypt hash string.
    Uses native bcrypt with automatic salt generation and UTF-8 encoding.
    Example: 'MyPass123' -> '$2b$12$K8yR2u...N6fT...'
    """
    # Defensive truncation to 72 bytes (bcrypt standard maximum length)
    password_bytes = plain_password.encode("utf-8")[:72]
    # Generate random cryptographic salt and compute hash
    salt = bcrypt.gensalt(rounds=12)
    hashed_bytes = bcrypt.hashpw(password_bytes, salt)
    return hashed_bytes.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Compares a candidate plain-text password against a stored bcrypt hash.
    Returns True if they match, False otherwise.
    """
    try:
        password_bytes = plain_password.encode("utf-8")[:72]
        hashed_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception:
        return False


def create_access_token(
    subject: str,
    role: str,
    secret_key: str,
    algorithm: str = "HS256",
    expires_delta: Optional[timedelta] = None,
    extra_claims: Optional[Dict[str, Any]] = None
) -> str:
    """
    Generates a cryptographically signed short-lived JWT Access Token.
    
    Parameters:
    - subject: The unique identifier of the user (e.g. user_id or email)
    - role: The authorization role of the user (e.g. 'candidate', 'recruiter', 'admin')
    - secret_key: Cryptographic HMAC key used to sign the token
    - algorithm: Hashing algorithm (default 'HS256')
    - expires_delta: Optional custom lifetime timedelta
    - extra_claims: Optional custom dictionary of metadata to embed into token payload
    """
    # Current timestamp in UTC
    now = datetime.now(timezone.utc)
    
    # Calculate expiration time (default to 30 minutes if not specified)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=30)
    
    # Construct the JWT payload dictionary
    payload: Dict[str, Any] = {
        # 'sub' stands for subject (the user identity)
        "sub": str(subject),
        # 'role' is used by RBAC (Role-Based Access Control) to gate sensitive endpoints
        "role": role,
        # 'iat' stands for Issued At (timestamp)
        "iat": int(now.timestamp()),
        # 'exp' stands for Expiration Time (timestamp)
        "exp": int(expire.timestamp()),
        # 'type' clarifies this is an access token, preventing misuse as a refresh token
        "token_type": "access"
    }
    
    # Append any additional custom metadata claims if provided
    if extra_claims:
        payload.update(extra_claims)
        
    # Sign and encode the payload into a compact URL-safe JWT string
    encoded_jwt = jwt.encode(payload, secret_key, algorithm=algorithm)
    return encoded_jwt


def create_refresh_token(
    subject: str,
    secret_key: str,
    algorithm: str = "HS256",
    expires_days: int = 7
) -> str:
    """
    Generates a long-lived JWT Refresh Token used solely to obtain new access tokens
    without forcing the user to repeatedly re-enter their username and password.
    """
    # Current timestamp in UTC
    now = datetime.now(timezone.utc)
    
    # Set expiration to specified number of days (default 7 days)
    expire = now + timedelta(days=expires_days)
    
    # Construct refresh token payload
    payload: Dict[str, Any] = {
        "sub": str(subject),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "token_type": "refresh"
    }
    
    # Sign the token
    encoded_jwt = jwt.encode(payload, secret_key, algorithm=algorithm)
    return encoded_jwt


def decode_and_verify_token(
    token: str,
    secret_key: str,
    algorithm: str = "HS256"
) -> Dict[str, Any]:
    """
    Validates a JWT token's signature, checks if it has expired, and decodes the claims.
    Raises jwt.ExpiredSignatureError if token is expired.
    Raises jwt.InvalidTokenError if signature is tampered or malformed.
    """
    # jwt.decode verifies signature AND ensures current time < exp claim
    payload = jwt.decode(token, secret_key, algorithms=[algorithm])
    return payload
