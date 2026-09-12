"""FastAPI bridge between the dashboard, Firebase, and odor ML pipeline."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.core.config import Settings
from app.services.firebase_service import FirebaseSensorService
from app.services.ml_service import MLPredictionService

logger = logging.getLogger(__name__)


def create_app(
    settings: Settings | None = None,
    firebase_service: Any | None = None,
    ml_service: Any | None = None,
) -> FastAPI:
    settings = settings or Settings.from_env(require_firebase=False)
    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "Bridge API for validated ESP32 sensor readings, Firebase Realtime "
            "Database access, and odor/intensity/anomaly predictions."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    firebase_initialization_error = None
    if firebase_service is None:
        try:
            firebase_service = FirebaseSensorService(settings)
        except Exception as exc:
            firebase_initialization_error = str(exc)
            logger.warning("Firebase unavailable at startup: %s", exc)

    ml_initialization_error = None
    if ml_service is None and settings.ml_model_path:
        try:
            ml_service = MLPredictionService(settings.ml_model_path)
        except Exception as exc:
            ml_initialization_error = str(exc)
            logger.warning("ML model unavailable at startup: %s", exc)

    app.state.settings = settings
    app.state.firebase_service = firebase_service
    app.state.ml_service = ml_service
    app.state.firebase_initialization_error = firebase_initialization_error
    app.state.ml_initialization_error = ml_initialization_error
    app.include_router(router)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        _request: Request, exc: RequestValidationError
    ):
        return JSONResponse(
            status_code=422,
            content={
                "detail": jsonable_encoder(exc.errors()),
                "error_code": "VALIDATION_ERROR",
            },
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(_request: Request, exc: HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail, "error_code": f"HTTP_{exc.status_code}"},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_request: Request, exc: Exception):
        logger.exception("Unhandled API error")
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "error_code": "INTERNAL_ERROR"},
        )

    return app


app = create_app()
