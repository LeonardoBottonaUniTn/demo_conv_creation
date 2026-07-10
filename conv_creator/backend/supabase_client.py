"""Shared Supabase client helpers used across the backend.

This module centralizes the creation of the Supabase client as well as
small utilities such as JWKS fetching. Keeping the logic in a single file
avoids scattering environment handling throughout the codebase and makes
it easier to mock during tests.
"""
from __future__ import annotations

import os
import time
from typing import Any, Dict

import httpx
from supabase import Client, create_client

# Cache the Supabase client so we only instantiate it once.
_supabase_client: Client | None = None

# Very small JWKS cache (60 seconds) so repeated auth checks don't hammer
# the Supabase endpoint.
_JWKS_CACHE: Dict[str, Any] = {"payload": None, "expires_at": 0.0}
_JWKS_TTL_SECONDS = 60.0


def _get_env_first(*names: str) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value:
            return value.strip()
    return None


def _is_http_url(value: str) -> bool:
    return value.startswith("http://") or value.startswith("https://")


def _resolve_supabase_url() -> str:
    # Prefer SUPABASE_URL: DATABASE_URL is often a postgres connection string.
    for env_name in ("SUPABASE_URL", "DATABASE_URL"):
        value = os.getenv(env_name)
        if value and _is_http_url(value):
            return value
    raise RuntimeError(
        "SUPABASE_URL (or an HTTP(S) DATABASE_URL) must be set before accessing Supabase."
    )


_ANON_KEY_ENV_NAMES = (
    "SUPABASE_ANON_KEY",
    "SUPABASE_PUBLISHABLE_KEY",
    "DATABASE_ANON_KEY",
    "DATABASE_PUBLISHABLE_KEY",
    "SUPABASE_KEY",
)


def _resolve_supabase_anon_key() -> str:
    value = _get_env_first(*_ANON_KEY_ENV_NAMES)
    if not value:
        raise RuntimeError(
            "Set one of DATABASE_ANON_KEY, SUPABASE_ANON_KEY, or SUPABASE_PUBLISHABLE_KEY "
            "before accessing Supabase."
        )
    return value


def get_supabase_client() -> Client:
    """Return a singleton Supabase client configured with the service key."""
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client

    supabase_url = _resolve_supabase_url()
    supabase_anon_key = _resolve_supabase_anon_key()

    _supabase_client = create_client(supabase_url, supabase_anon_key)
    return _supabase_client


def get_supabase_url() -> str:
    return _resolve_supabase_url()


def get_supabase_anon_key() -> str:
    return _resolve_supabase_anon_key()


def _resolve_service_role_key() -> str:
    value = _get_env_first("SUPABASE_SERVICE_ROLE_KEY", "SERVICE_ROLE_KEY")
    if not value:
        raise RuntimeError(
            "SUPABASE_SERVICE_ROLE_KEY must be set for Supabase Storage operations."
        )
    return value


_supabase_service_client: Client | None = None


def get_supabase_service_client() -> Client:
    """Return a singleton Supabase client using the service role key."""
    global _supabase_service_client
    if _supabase_service_client is not None:
        return _supabase_service_client

    _supabase_service_client = create_client(
        _resolve_supabase_url(),
        _resolve_service_role_key(),
    )
    return _supabase_service_client


def get_jwks() -> Dict[str, Any]:
    """Fetch (and cache briefly) the JWKS published by Supabase Auth."""
    now = time.time()
    cached = _JWKS_CACHE["payload"]
    if cached and now < _JWKS_CACHE["expires_at"]:
        return cached

    url = f"{get_supabase_url().rstrip('/')}/auth/v1/.well-known/jwks.json"
    try:
        response = httpx.get(url, timeout=10.0)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise RuntimeError(f"Failed to download Supabase JWKS: {exc}") from exc

    payload = response.json()
    _JWKS_CACHE["payload"] = payload
    _JWKS_CACHE["expires_at"] = now + _JWKS_TTL_SECONDS
    return payload
