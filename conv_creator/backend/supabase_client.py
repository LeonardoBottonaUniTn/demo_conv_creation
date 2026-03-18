"""Shared Supabase client helpers used across the backend.

This module centralizes the creation of the Supabase client as well as
small utilities such as JWKS fetching. Keeping the logic in a single file
avoids scattering environment handling throughout the codebase and makes
it easier to mock during tests.
"""
from __future__ import annotations

import os
import time
from typing import Any, Dict, Sequence

import httpx
from supabase import Client, create_client

# Cache the Supabase client so we only instantiate it once.
_supabase_client: Client | None = None

# Very small JWKS cache (60 seconds) so repeated auth checks don't hammer
# the Supabase endpoint.
_JWKS_CACHE: Dict[str, Any] = {"payload": None, "expires_at": 0.0}
_JWKS_TTL_SECONDS = 60.0

_DEFAULT_PROFILE = "cloud"
_PROFILE_ENV_VAR = "SUPABASE_PROFILE"


def _active_profile() -> str:
    raw = os.getenv(_PROFILE_ENV_VAR, _DEFAULT_PROFILE)
    profile = (raw or _DEFAULT_PROFILE).strip().lower()
    return profile or _DEFAULT_PROFILE


def _candidate_env_names(base: str, legacy: Sequence[str]) -> list[str]:
    profile = _active_profile()
    names: list[str] = []
    prefix = profile.upper() if profile else ""
    if prefix:
        names.append(f"{prefix}_{base}")
        for legacy_name in legacy:
            names.append(f"{prefix}_{legacy_name}")
    names.append(base)
    names.extend(legacy)

    ordered: list[str] = []
    seen: set[str] = set()
    for name in names:
        norm = name.strip()
        if not norm or norm in seen:
            continue
        ordered.append(norm)
        seen.add(norm)
    return ordered


def _read_env(base: str, legacy: Sequence[str] = (), *, required: bool = True) -> str | None:
    for env_name in _candidate_env_names(base, legacy):
        value = os.getenv(env_name)
        if value:
            return value
    if required:
        candidates = ", ".join(_candidate_env_names(base, legacy))
        raise RuntimeError(
            f"Missing Supabase setting for profile '{_active_profile()}'. Set one of: {candidates}."
        )
    return None


def get_active_supabase_profile() -> str:
    """Return the currently selected Supabase profile (cloud/local/etc.)."""
    return _active_profile()


def get_supabase_url() -> str:
    value = _read_env("SUPABASE_URL", legacy=("DATABASE_URL",))
    if not value:
        raise RuntimeError("SUPABASE_URL is not configured.")
    return value


def get_supabase_anon_key() -> str:
    value = _read_env(
        "SUPABASE_ANON_KEY",
        legacy=("SUPABASE_KEY", "DATABASE_ANON_KEY", "DATABASE_PUBLISHABLE_KEY"),
    )
    if not value:
        raise RuntimeError("Supabase anon/public key is not configured.")
    return value


def get_supabase_service_role_key() -> str:
    value = _read_env("SUPABASE_SERVICE_ROLE_KEY", legacy=("SERVICE_ROLE_KEY",))
    if not value:
        raise RuntimeError("Supabase service role key is not configured.")
    return value


def get_supabase_db_url(required: bool = True) -> str | None:
    return _read_env(
        "SUPABASE_DB_URL",
        legacy=("DATABASE_IPv4_URL", "DATABASE_URL"),
        required=required,
    )


def get_supabase_client() -> Client:
    """Return a singleton Supabase client configured with the service key."""
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client

    supabase_url = get_supabase_url()
    anon_key = get_supabase_anon_key()

    _supabase_client = create_client(supabase_url, anon_key)
    return _supabase_client


def get_jwks() -> Dict[str, Any]:
    """Fetch (and cache briefly) the JWKS published by Supabase Auth."""
    now = time.time()
    cached = _JWKS_CACHE["payload"]
    if cached and now < _JWKS_CACHE["expires_at"]:
        return cached

    url = f"{get_supabase_url().rstrip('/')}/auth/v1/keys"
    try:
        response = httpx.get(url, timeout=10.0)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise RuntimeError(f"Failed to download Supabase JWKS: {exc}") from exc

    payload = response.json()
    _JWKS_CACHE["payload"] = payload
    _JWKS_CACHE["expires_at"] = now + _JWKS_TTL_SECONDS
    return payload
