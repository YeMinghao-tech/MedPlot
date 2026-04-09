"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from src.core.settings import load_settings, Settings
from src.api.routers import chat, session, patient
from src.api.middleware.auth import AuthMiddleware
from src.agent.planner.router import Router
from src.libs.llm.llm_factory import LLMFactory
from src.libs.his.his_factory import HISFactory
from src.tools.his_orchestrator.schedule_service import ScheduleService
from src.tools.his_orchestrator.dept_service import DepartmentService
from src.tools.his_orchestrator.booking_service import BookingService

logger = logging.getLogger(__name__)

# Global settings instance
_app_settings: Settings = None


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance.
    """
    global _app_settings

    # Load settings
    config_path = Path("config/settings.yaml")
    if config_path.exists():
        _app_settings = load_settings(str(config_path))
    else:
        # Use defaults for testing
        _app_settings = None

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Application lifespan handler."""
        # Startup: Initialize router
        logger.info("MedPilot API starting up...")
        app.state.router = _create_router(_app_settings)
        logger.info("Router initialized")
        yield
        # Shutdown
        logger.info("MedPilot API shutting down...")

    app = FastAPI(
        title="MedPilot API",
        description="个性化医疗导诊 Agent API",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Configure CORS
    if _app_settings and _app_settings.api:
        cors_origins = _app_settings.api.cors_origins or ["*"]
    else:
        cors_origins = ["*"]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add auth middleware
    app.add_middleware(AuthMiddleware)

    # Register routers
    app.include_router(session.router, prefix="/sessions", tags=["sessions"])
    app.include_router(chat.router, prefix="/chat", tags=["chat"])
    app.include_router(patient.router, prefix="/patients", tags=["patients"])

    @app.get("/")
    async def root():
        """Root endpoint."""
        return {
            "name": "MedPilot API",
            "version": "0.1.0",
            "status": "running",
        }

    @app.get("/health")
    async def health(request: Request):
        """Health check endpoint with dependency check."""
        router: Optional[Router] = getattr(request.app.state, 'router', None)
        return {
            "status": "healthy",
            "router_initialized": router is not None
        }

    return app


def _create_router(settings: Optional[Settings]) -> Router:
    """Create and configure the router instance.

    Args:
        settings: Application settings.

    Returns:
        Configured Router instance.
    """
    llm_client = None
    if settings and settings.llm and settings.llm.api_key:
        try:
            llm_client = LLMFactory.create(settings)
            logger.info(f"LLM client created: {llm_client}")
        except Exception as e:
            logger.error(f"Failed to create LLM client: {e}")

    his_client = None
    if settings and settings.his:
        try:
            his_client = HISFactory.create(settings)
            logger.info(f"HIS client created: {his_client}")
        except Exception as e:
            logger.warning(f"Failed to create HIS client: {e}")

    schedule_service = ScheduleService(his_client) if his_client else None
    dept_service = DepartmentService(his_client) if his_client else None
    booking_service = BookingService(his_client) if his_client else None

    return Router(
        llm_client=llm_client,
        schedule_service=schedule_service,
        department_service=dept_service,
        booking_service=booking_service,
    )


def get_settings() -> Settings:
    """Get application settings."""
    return _app_settings
