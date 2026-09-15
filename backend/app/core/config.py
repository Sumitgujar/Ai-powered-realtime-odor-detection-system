"""Environment-based configuration for ingestion and API services."""

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
    predictions_path: str = "predictions"
    alerts_path: str = "alerts"
    ml_model_path: str | None = None
    cors_origins: tuple[str, ...] = ("http://localhost:5173",)
    log_level: str = "INFO"
    app_name: str = "AI-Powered Real-Time Odor Detection API"
    app_version: str = "0.2.0"

    @classmethod
    def from_env(
        cls,
        env_file: str | Path | None = None,
        require_firebase: bool = True,
    ) -> "Settings":
        backend_dir = Path(__file__).resolve().parents[2]
        project_dir = backend_dir.parent
        default_env = backend_dir / ".env"
        load_dotenv(Path(env_file) if env_file else default_env)

        project_id = os.getenv("FIREBASE_PROJECT_ID", "").strip()
        database_url = os.getenv("FIREBASE_DATABASE_URL", "").strip()
        credentials_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "").strip() or None
        sensor_data_path = os.getenv("FIREBASE_SENSOR_DATA_PATH", "sensor_readings").strip("/")
        predictions_path = os.getenv("FIREBASE_PREDICTIONS_PATH", "predictions").strip("/")
        alerts_path = os.getenv("FIREBASE_ALERTS_PATH", "alerts").strip("/")
        model_path_value = os.getenv(
            "ML_MODEL_PATH", str(project_dir / "ml" / "models" / "odor_pipeline.joblib")
        ).strip()
        origins = tuple(
            origin.strip()
            for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
            if origin.strip()
        )
        log_level = os.getenv("LOG_LEVEL", "INFO").strip().upper()

        missing = [
            name
            for name, value in (
                ("FIREBASE_PROJECT_ID", project_id),
                ("FIREBASE_DATABASE_URL", database_url),
            )
            if not value
        ]
        if require_firebase and missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
        if database_url and not database_url.startswith(
            ("https://", "http://localhost", "http://127.0.0.1")
        ):
            raise ValueError("FIREBASE_DATABASE_URL must be HTTPS or a local emulator URL")
        for name, value in (
            ("FIREBASE_SENSOR_DATA_PATH", sensor_data_path),
            ("FIREBASE_PREDICTIONS_PATH", predictions_path),
            ("FIREBASE_ALERTS_PATH", alerts_path),
        ):
            if not value:
                raise ValueError(f"{name} cannot be empty")
        if not origins:
            raise ValueError("CORS_ORIGINS must contain at least one origin")

        def resolve_optional_path(value: str | None) -> str | None:
            if not value:
                return None
            path = Path(value).expanduser()
            if not path.is_absolute():
                path = backend_dir / path
            return str(path.resolve())

        return cls(
            firebase_project_id=project_id,
            firebase_database_url=database_url,
            firebase_credentials_path=resolve_optional_path(credentials_path),
            sensor_data_path=sensor_data_path,
            predictions_path=predictions_path,
            alerts_path=alerts_path,
            ml_model_path=resolve_optional_path(model_path_value),
            cors_origins=origins,
            log_level=log_level,
        )
