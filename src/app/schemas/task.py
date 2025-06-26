# app/schemas/task.py
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.task import TaskPriority, TaskStatus


class TaskBase(BaseModel):
    """Base task schema with common fields."""

    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=1000)
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: datetime | None = None


class TaskCreate(TaskBase):
    """Schema for task creation."""

    pass


class TaskUpdate(BaseModel):
    """Schema for task updates."""

    title: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=1000)
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    due_date: datetime | None = None


class TaskResponse(TaskBase):
    """Schema for task responses."""

    id: UUID
    status: TaskStatus
    owner_id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
