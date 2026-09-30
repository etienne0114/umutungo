import argparse
import os
from pathlib import Path

from govasset_api.supabase_admin import (
    SupabaseAdminError,
    list_supabase_users,
    update_supabase_user_app_metadata,
)


def load_env_file(path: Path) -> None:
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Grant trusted administrator and API access to an existing confirmed user."
    )
    parser.add_argument(
        "--email",
        default="etiennetuyihamye@gmail.com",
        help="Exact Supabase Auth email to promote (default: requested admin account).",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        help="Optional ignored env file containing SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY.",
    )
    args = parser.parse_args()
    if args.env_file:
        load_env_file(args.env_file)

    target = args.email.strip().casefold()
    try:
        matches = [
            user
            for user in list_supabase_users()
            if isinstance(user.get("email"), str)
            and user["email"].strip().casefold() == target
        ]
        if len(matches) != 1:
            print(
                "Expected exactly one existing Supabase user with that email; "
                "register and confirm the account before promoting it."
            )
            return 1

        user = matches[0]
        if not user.get("email_confirmed_at"):
            print("The target account must confirm its email before administrator promotion.")
            return 1
        user_id = str(user["id"])
        metadata = user.get("app_metadata")
        metadata = dict(metadata) if isinstance(metadata, dict) else {}
        metadata.update({"govasset_access": "approved", "govasset_role": "admin"})
        updated = update_supabase_user_app_metadata(user_id, metadata)
        updated_metadata = updated.get("app_metadata")
        if (
            not isinstance(updated_metadata, dict)
            or updated_metadata.get("govasset_access") != "approved"
            or updated_metadata.get("govasset_role") != "admin"
        ):
            print("Supabase did not return the expected administrator metadata.")
            return 1
    except SupabaseAdminError as exc:
        print(f"Could not promote administrator: {exc}")
        return 1

    print(f"Administrator access granted to {args.email.strip()}.")
    print("The user must sign out and sign back in to refresh their access token.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
