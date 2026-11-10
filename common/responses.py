# ==============================================================================
# CALYX COMMON MODULE: STANDARDIZED API RESPONSE ENVELOPES
# ==============================================================================
# Concept Explanation for Beginners:
# In large microservice ecosystems, having Service A return `{"status": "ok"}`
# while Service B returns `{"result": "success"}` and Service C returns `{"data": [...]}`
# creates chaotic frontend code and breaks client SDKs.
# A "Response Envelope Pattern" guarantees that every single endpoint across ALL
# 5 microservices wraps its responses in a strictly consistent JSON structure.
# If an error happens, the envelope provides error codes, human messages, and timestamps.
# ==============================================================================

from datetime import datetime, timezone
from typing import Any, Optional, Dict
from pydantic import BaseModel, Field


class StandardResponse(BaseModel):
    """
    Standard successful API response envelope.
    Ensures every microservice in the cluster outputs uniform data structures.
    """
    # Indicates whether the operation succeeded
    success: bool = Field(default=True, description="True if request succeeded, False otherwise")
    
    # Human-readable descriptive message (e.g. 'User created successfully', 'Job posted')
    message: str = Field(default="Operation completed successfully", description="Descriptive status message")
    
    # The actual payload (dictionary, list, or primitive value)
    data: Optional[Any] = Field(default=None, description="The response data payload")
    
    # UTC ISO-8601 timestamp of when the response was generated
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 UTC timestamp of response generation"
    )


class ErrorDetail(BaseModel):
    """
    Detailed error description structure.
    """
    # Machine-readable error code (e.g., 'INVALID_CREDENTIALS', 'ENTITY_NOT_FOUND', 'VALIDATION_FAILED')
    code: str = Field(..., description="Unique machine-readable error string")
    
    # Human-readable explanation of why the failure occurred
    message: str = Field(..., description="Explanation of error for developer or user")
    
    # Optional nested details (e.g., field-specific validation error list)
    details: Optional[Any] = Field(default=None, description="Additional context or validation failure list")


class StandardErrorResponse(BaseModel):
    """
    Standard error response envelope.
    Returned whenever HTTP status >= 400 occurs.
    """
    # Always False for error responses
    success: bool = Field(default=False, description="Always False on errors")
    
    # Error metadata block
    error: ErrorDetail = Field(..., description="Structured error information")
    
    # UTC ISO-8601 timestamp
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 UTC timestamp of error"
    )
