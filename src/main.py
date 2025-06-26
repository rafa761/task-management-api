# main.py
import uvicorn

from app.core.config import get_settings
from app.core.factory import create_app

# Create the FastAPI application instance using the factory pattern
app = create_app()

if __name__ == "__main__":
    """
    Development server entry point.
    In production, this will be replaced by a WSGI/ASGI server like Gunicorn + Uvicorn workers.
    """
    settings = get_settings()

    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
        access_log=True,
    )
