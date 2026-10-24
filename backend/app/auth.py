"""
UrbanSage AI — Server-Side Authentication & Authorization Security Module
========================================================================
Implements JWT authentication, API Key fallbacks, and Role-Based Access
Control (RBAC) to protect administrative decision-support endpoints and
privileged lifecycle operations.

Roles:
- `administrator`: Municipal officers, environmental engineers, department heads.
- `contractor`: Field remediation agents and public works contractors.
- `citizen`: General public reporting environmental issues.
- `system`: Automated background routines and cron monitors.

Security Design:
----------------
- Standard `Bearer <JWT>` header via HTTPAuthorizationCredentials.
- Development API-Key header (`X-Admin-API-Key` or `X-API-Key`) configurable via
  `ADMIN_API_KEY` environment variable.
- Default development test token support when offline.
- Explicit HTTP 401 Unauthorized for missing/invalid credentials.
- Explicit HTTP 403 Forbidden for insufficient permissions (e.g. citizen role
  attempting administrator dispatch or status mutation).
- Never leaks private credentials or reporter contact information.
"""

from __future__ import annotations

import datetime
from datetime import timezone
import logging
import os
from typing import Any, Literal, Optional
import jwt
from fastapi import Depends, Header, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

logger = logging.getLogger("urbansage.auth")

# JWT configuration from environment
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "urbansage-mvp-stabilization-secret-key-32chars")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "urbansage-admin-dev-key")

# Optional bearer scheme
bearer_scheme = HTTPBearer(auto_error=False)

from jwt import PyJWKClient

# Supabase Auth JWKS client
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://lrkjcavnvabqbrpjgpbq.supabase.co")
_jwks_url = f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json" if SUPABASE_URL else None
_jwks_client: Optional[PyJWKClient] = None

def get_jwks_client() -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        if not _jwks_url:
            raise ValueError("SUPABASE_URL not configured for JWKS validation.")
        _jwks_client = PyJWKClient(_jwks_url, cache_keys=True, lifespan=3600)
    return _jwks_client

RoleType = Literal["administrator", "contractor", "citizen", "system"]


class AuthenticatedUser(BaseModel):
    """Authenticated caller identity with associated roles and permissions."""
    user_id: str
    role: RoleType
    email: Optional[str] = None
    name: Optional[str] = None
    department: Optional[str] = None
    vendor_id: Optional[str] = None

    @property
    def is_admin(self) -> bool:
        return self.role in ("administrator", "system")

    @property
    def is_contractor(self) -> bool:
        return self.role in ("contractor", "administrator", "system")


def create_access_token(
    user_id: str,
    role: RoleType = "administrator",
    email: Optional[str] = None,
    name: Optional[str] = None,
    department: Optional[str] = None,
    vendor_id: Optional[str] = None,
    expires_in_hours: int = 24,
) -> str:
    """Generate a signed JWT access token for an authenticated user."""
    now = datetime.datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "role": role,
        "email": email,
        "name": name,
        "department": department,
        "vendor_id": vendor_id,
        "iat": now,
        "exp": now + datetime.timedelta(hours=expires_in_hours),
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> AuthenticatedUser:
    """Validate and decode a Supabase Auth JWT (ES256) or internal JWT (HS256)."""
    try:
        header = jwt.get_unverified_header(token)
        alg = header.get("alg", "HS256")

        if alg == "ES256":
            # Asymmetric verification via Supabase JWKS endpoint
            client = get_jwks_client()
            signing_key = client.get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["ES256"],
                audience="authenticated",
                issuer=f"{SUPABASE_URL}/auth/v1",
            )
        else:
            # Symmetric verification via backend JWT_SECRET_KEY
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])

        # Extract authoritative role from server-controlled app_metadata or payload
        app_metadata = payload.get("app_metadata", {})
        user_metadata = payload.get("user_metadata", {})

        app_role = app_metadata.get("role")
        if app_role in ("administrator", "contractor", "citizen"):
            role: RoleType = app_role
        elif payload.get("role") in ("administrator", "contractor", "citizen", "system"):
            role = payload.get("role")
        else:
            # All public accounts strictly default to citizen
            role = "citizen"

        dept = app_metadata.get("department") or user_metadata.get("department") or payload.get("department")
        vendor = app_metadata.get("vendor_id") or user_metadata.get("vendor_id") or payload.get("vendor_id")
        user_name = user_metadata.get("full_name") or payload.get("name") or payload.get("email")

        return AuthenticatedUser(
            user_id=payload.get("sub", "unknown"),
            role=role,
            email=payload.get("email"),
            name=user_name,
            department=dept,
            vendor_id=vendor,
        )
    except jwt.ExpiredSignatureError as e:
        logger.warning("Token expired: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
    except (jwt.InvalidTokenError, Exception) as e:
        logger.warning("Invalid token: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


async def get_current_user(
    auth: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
    x_admin_api_key: Optional[str] = Header(default=None, alias="X-Admin-API-Key"),
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
) -> AuthenticatedUser:
    """
    Enforce authentication via Bearer JWT or configured Admin API Key.
    Raises HTTP 401 Unauthorized if missing, expired, or invalid.
    """
    # 1. Check API Key header
    provided_key = x_admin_api_key or x_api_key
    if provided_key:
        app_env = os.getenv("APP_ENV", "development").strip().lower()
        if provided_key == "urbansage-admin-dev-key":
            if app_env == "production":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Development fallback API Key is prohibited in production.",
                )
            return AuthenticatedUser(
                user_id="dev-fallback-admin",
                role="administrator",
                email="dev-fallback@urbansage.local",
                name="Development Administrator (Fallback Key)",
                department="Municipal Control Room (Dev)",
            )

        if ADMIN_API_KEY and provided_key == ADMIN_API_KEY:
            return AuthenticatedUser(
                user_id="admin-api-key-caller",
                role="administrator",
                email="admin-key@urbansage.local",
                name="System Administrator (API Key)",
                department="Municipal Control Room",
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key provided.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 2. Check Bearer JWT token
    if not auth or not auth.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please provide a valid Bearer token or Admin API Key.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return decode_access_token(auth.credentials)


async def require_admin_role(
    user: AuthenticatedUser = Depends(get_current_user),
) -> AuthenticatedUser:
    """
    Enforce administrator role for privileged municipal operations.
    Raises HTTP 403 Forbidden if user lacks administrator permissions.
    """
    if not user.is_admin:
        logger.warning(
            "Access forbidden: User %s with role '%s' attempted admin action.",
            user.user_id,
            user.role,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: Action requires 'administrator' role, but user has '{user.role}'.",
        )
    return user


async def require_admin_or_contractor(
    user: AuthenticatedUser = Depends(get_current_user),
) -> AuthenticatedUser:
    """Enforce contractor or administrator role for field work completion updates."""
    if not user.is_contractor:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Action requires 'contractor' or 'administrator' role.",
        )
    return user
