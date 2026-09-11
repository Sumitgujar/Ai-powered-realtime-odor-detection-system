"""Environment-based application configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    firebase_project_id: str
    firebase_database_url: str
    firebase_credentials_path: str | None
    sensor_data_path: str = "sensor_readings"

    @classmethod
    def from_env(cls, env_file: str | Path | None = None) -> "Settings":
        default_env = Path(__file__).resolve().parents[2] / ".env"
        load_dotenv(Path(env_file) if env_file else default_env)

        project_id = os.getenv("FIREBASE_PROJECT_ID", "").strip()
        database_url = os.getenv("FIREBASE_DATABASE_URL", "").strip()
        credentials_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "").strip() or None
        sensor_data_path = os.getenv("FIREBASE_SENSOR_DATA_PATH", "sensor_readings").strip("/")

        missing = [
            name
            for name, value in (
                ("FIREBASE_PROJECT_ID", project_id),
                ("FIREBASE_DATABASE_URL", database_url),
            )
            if not value
        ]
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
        if not database_url.startswith(("https://", "http://localhost", "http://127.0.0.1")):
            raise ValueError("FIREBASE_DATABASE_URL must be HTTPS or a local emulator URL")
        if not sensor_data_path:
            raise ValueError("FIREBASE_SENSOR_DATA_PATH cannot be empty")

        if credentials_path:
            credential_file = Path(credentials_path).expanduser()
            if not credential_file.is_absolute():
                credential_file = default_env.parent / credential_file
            credentials_path = str(credential_file.resolve())

        return cls(project_id, database_url, credentials_path, sensor_data_path)
