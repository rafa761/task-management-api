# app/routers/__init__.py
from .auth import router as auth_router
from .tasks import router as tasks_router
from .users import router as users_router

__all__ = ["auth_router", "users_router", "tasks_router"]
