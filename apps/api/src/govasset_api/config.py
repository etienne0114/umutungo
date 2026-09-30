import os
from pathlib import Path

from dotenv import load_dotenv

API_ROOT = Path(__file__).resolve().parents[2]
LOCAL_ENV_FILE = API_ROOT / ".env.local"


def load_local_environment(env_file: Path = LOCAL_ENV_FILE) -> None:
    runtime = os.getenv("APP_ENV", "").strip().lower()
    if (
        os.getenv("RENDER_SERVICE_ID")
        or runtime in {"production", "prod"}
    ):
        return
    load_dotenv(env_file, override=False)
