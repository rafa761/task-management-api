# app/services/task_service.py
from collections.abc import Sequence

from fastapi import HTTPException, status

from app.models.task import Task, TaskStatus
from app.repositories.task_repository import TaskRepository
from app.schemas.task import TaskCreate, TaskUpdate


class TaskService:
    """Service for task operations."""

    def __init__(self, task_repository: TaskRepository):
        self.task_repository = task_repository

    async def create_task(self, task_data: TaskCreate, owner_id: int) -> Task:
        """Create a new task."""
        task = await self.task_repository.create(
            **task_data.model_dump(), owner_id=owner_id
        )
        return task

    async def get_user_tasks(
        self, owner_id: int, skip: int = 0, limit: int = 100
    ) -> Sequence[Task]:
        """Get all tasks for a user."""
        return await self.task_repository.get_by_owner(owner_id, skip, limit)

    async def get_task_by_id(self, task_id: int, owner_id: int) -> Task:
        """Get task by ID (ensuring ownership)."""
        task = await self.task_repository.get_by_owner_and_id(owner_id, task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
            ) from None
        return task

    async def update_task(
        self, task_id: int, task_data: TaskUpdate, owner_id: int
    ) -> Task:
        """Update task (ensuring ownership)."""
        # Verify task exists and belongs to user
        await self.get_task_by_id(task_id, owner_id)

        # Update task
        updated_task = await self.task_repository.update(
            task_id, **task_data.model_dump(exclude_unset=True)
        )

        if not updated_task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
            ) from None

        return updated_task

    async def delete_task(self, task_id: int, owner_id: int) -> bool:
        """Delete task (ensuring ownership)."""
        # Verify task exists and belongs to user
        await self.get_task_by_id(task_id, owner_id)

        # Delete task
        return await self.task_repository.delete(task_id)

    async def get_tasks_by_status(
        self, owner_id: int, status: TaskStatus, skip: int = 0, limit: int = 100
    ) -> Sequence[Task]:
        """Get tasks by status for a user."""
        return await self.task_repository.get_by_status(owner_id, status, skip, limit)
