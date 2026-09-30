import os
from functools import lru_cache
from typing import Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from jwt.exceptions import PyJWKClientConnectionError, PyJWTError

bearer_scheme = HTTPBearer(auto_error=False)


class UserAccessNotApproved(Exception):
    pass


def authentication_required() -> bool:
    return os.getenv("AUTH_REQUIRED", "true").strip().lower() in {"1", "true", "yes"}


def supabase_url() -> str | None:
    value = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
    return value or None


@lru_cache(maxsize=4)
def _jwks_client(url: str) -> PyJWKClient:
    return PyJWKClient(
        f"{url}/auth/v1/.well-known/jwks.json",
        cache_jwk_set=True,
        lifespan=300,
        timeout=5,
    )


def verify_supabase_token(token: str, project_url: str) -> dict[str, Any]:
    signing_key = _jwks_client(project_url).get_signing_key_from_jwt(token)
    claims = jwt.decode(
        token,
        signing_key.key,
        algorithms=["ES256", "RS256"],
        audience="authenticated",
        issuer=f"{project_url}/auth/v1",
        options={"require": ["exp", "iat", "iss", "sub", "aud"]},
    )
    app_metadata = claims.get("app_metadata")
    if not isinstance(claims.get("sub"), str) or claims.get("role") != "authenticated":
        raise jwt.InvalidTokenError("The token is not an authenticated user token.")
    if not isinstance(app_metadata, dict) or app_metadata.get("govasset_access") != "approved":
        raise UserAccessNotApproved
    return claims


def require_authenticated_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict[str, Any] | None:
    if not authentication_required():
        return None

    project_url = supabase_url()
    if project_url is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Supabase authentication is required but SUPABASE_URL is not configured.",
        )
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="A valid Supabase access token is required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        return verify_supabase_token(credentials.credentials, project_url)
    except UserAccessNotApproved as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is awaiting administrator approval.",
        ) from exc
    except PyJWKClientConnectionError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not retrieve Supabase signing keys.",
        ) from exc
    except PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="The Supabase access token is invalid or expired.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def require_admin_user(
    claims: dict[str, Any] | None = Depends(require_authenticated_user),
) -> dict[str, Any]:
    app_metadata = claims.get("app_metadata") if claims is not None else None
    if not isinstance(app_metadata, dict) or app_metadata.get("govasset_role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access is required.",
        )
    return claims
