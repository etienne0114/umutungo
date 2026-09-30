import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from govasset_api.auth import supabase_url


class SupabaseAdminError(Exception):
    pass


def _admin_request(path: str, method: str = "GET", payload: dict[str, Any] | None = None):
    project_url = supabase_url()
    service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if project_url is None or not service_key:
        raise SupabaseAdminError("Supabase administrator API is not configured.")

    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Accept": "application/json",
    }
    body = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(payload).encode()

    request = Request(
        f"{project_url}/auth/v1/admin/{path.lstrip('/')}",
        data=body,
        headers=headers,
        method=method,
    )
    try:
        with urlopen(request, timeout=15) as response:
            return json.load(response)
    except HTTPError as exc:
        raise SupabaseAdminError(
            f"Supabase administrator API returned HTTP {exc.code}."
        ) from exc
    except (URLError, TimeoutError) as exc:
        raise SupabaseAdminError("Could not reach the Supabase administrator API.") from exc
    except json.JSONDecodeError as exc:
        raise SupabaseAdminError("Supabase administrator API returned invalid JSON.") from exc


def list_supabase_users(limit: int = 1000) -> list[dict[str, Any]]:
    users: list[dict[str, Any]] = []
    per_page = 100
    for page in range(1, (limit + per_page - 1) // per_page + 1):
        response = _admin_request(f"users?page={page}&per_page={per_page}")
        page_users = response.get("users") if isinstance(response, dict) else None
        if not isinstance(page_users, list):
            raise SupabaseAdminError("Supabase administrator API returned an invalid user list.")
        users.extend(user for user in page_users if isinstance(user, dict))
        if len(page_users) < per_page or len(users) >= limit:
            break
    return users[:limit]


def get_supabase_user(user_id: str) -> dict[str, Any]:
    response = _admin_request(f"users/{user_id}")
    user = response.get("user", response) if isinstance(response, dict) else None
    if not isinstance(user, dict):
        raise SupabaseAdminError("Supabase administrator API returned an invalid user.")
    return user


def update_supabase_user_app_metadata(
    user_id: str, app_metadata: dict[str, Any]
) -> dict[str, Any]:
    response = _admin_request(
        f"users/{user_id}",
        method="PUT",
        payload={"app_metadata": app_metadata},
    )
    user = response.get("user", response) if isinstance(response, dict) else None
    if not isinstance(user, dict):
        raise SupabaseAdminError("Supabase administrator API returned an invalid user.")
    return user
