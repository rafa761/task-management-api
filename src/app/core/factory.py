# app/core/factory.py
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings


def create_app() -> FastAPI:
    """
    Application factory function.
    Creates and configures a FastAPI application instance

    :return: Configured FastAPI application instance
    """
    # Create FastAPI instance
    app = FastAPI(
        title="Task Management API",
        description="Task management system",
        version="1.0.0",
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        openapi_url="/openapi.json" if settings.DEBUG else None,
    )

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Security Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Health check endpoint
    @app.get("/health", tags=["system"])
    async def health_check():
        """
        Health check endpoint for load balancers and monitoring systems.
        """
        return {
            "status": "healthy",
            "version": "1.0.0",
            "environment": settings.ENVIRONMENT,
        }

    # Root endpoint
    @app.get("/", tags=["system"])
    async def root():
        """API root endpoint with basic information."""
        return {
            "message": "Task Management API",
            "version": "1.0.0",
            "docs": "/docs" if settings.DEBUG else "Documentation disabled",
        }

    return app
