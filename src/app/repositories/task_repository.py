# app/repositories/task_repository.py
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task, TaskStatus

from .base_repository import BaseRepository


class TaskRepository(BaseRepository[Task]):
    """Repository for Task operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, Task)

    async def get_by_owner(
        self, owner_id: int, skip: int = 0, limit: int = 100
    ) -> Sequence[Task]:
        """Get tasks by owner."""
        result = await self.session.execute(
            select(Task)
            .where(Task.owner_id == owner_id)
            .offset(skip)
            .limit(limit)
            .order_by(Task.created_at.desc())
        )
        return result.scalars().all()

    async def get_by_owner_and_id(self, owner_id: int, task_id: int) -> Task | None:
        """Get specific task by owner and task ID."""
        result = await self.session.execute(
            select(Task).where(Task.owner_id == owner_id, Task.id == task_id)
        )
        return result.scalar_one_or_none()

    async def get_by_status(
        self, owner_id: int, status: TaskStatus, skip: int = 0, limit: int = 100
    ) -> Sequence[Task]:
        """Get tasks by owner and status."""
        result = await self.session.execute(
            select(Task)
            .where(Task.owner_id == owner_id, Task.status == status)
            .offset(skip)
            .limit(limit)
            .order_by(Task.created_at.desc())
        )
        return result.scalars().all()
