"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.settings import load_settings, Settings
from src.api.routers import chat, session, patient
from src.api.middleware.auth import AuthMiddleware


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
        # Startup
        print("MedPilot API starting up...")
        yield
        # Shutdown
        print("MedPilot API shutting down...")

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
    async def health():
        """Health check endpoint."""
        return {"status": "healthy"}

    return app


def get_settings() -> Settings:
    """Get application settings."""
    return _app_settings
