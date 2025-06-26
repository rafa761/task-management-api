# app/routers/tasks.py
from uuid import UUID

from fastapi import APIRouter, Query, status

from app.dependencies import CurrentUser, TaskServiceDep
from app.models.task import TaskStatus
from app.schemas.task import TaskCreate, TaskResponse, TaskUpdate

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_data: TaskCreate, current_user: CurrentUser, task_service: TaskServiceDep
) -> TaskResponse:
    """
    Create a new task.

    - **title**: Task title (required)
    - **description**: Task description (optional)
    - **priority**: Task priority (low, medium, high)
    - **due_date**: Task due date (optional)
    """
    task = await task_service.create_task(task_data, current_user.id)
    return TaskResponse.model_validate(task)


@router.get("/", response_model=list[TaskResponse])
async def get_tasks(
    current_user: CurrentUser,
    task_service: TaskServiceDep,
    status_filter: TaskStatus | None = Query(None, description="Filter by task status"),
    skip: int = Query(0, ge=0, description="Number of tasks to skip"),
    limit: int = Query(100, ge=1, le=100, description="Number of tasks to return"),
) -> list[TaskResponse]:
    """
    Get all tasks for the current user.

    - **status**: Filter by task status (optional)
    - **skip**: Number of tasks to skip for pagination
    - **limit**: Maximum number of tasks to return
    """
    if status_filter:
        tasks = await task_service.get_tasks_by_status(
            current_user.id, status_filter, skip, limit
        )
    else:
        tasks = await task_service.get_user_tasks(current_user.id, skip, limit)

    return [TaskResponse.model_validate(task) for task in tasks]


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: UUID, current_user: CurrentUser, task_service: TaskServiceDep
) -> TaskResponse:
    """Get a specific task by ID."""
    task = await task_service.get_task_by_id(task_id, current_user.id)
    return TaskResponse.model_validate(task)


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: UUID,
    task_data: TaskUpdate,
    current_user: CurrentUser,
    task_service: TaskServiceDep,
) -> TaskResponse:
    """Update a specific task."""
    task = await task_service.update_task(task_id, task_data, current_user.id)
    return TaskResponse.model_validate(task)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: UUID, current_user: CurrentUser, task_service: TaskServiceDep
) -> None:
    """Delete a specific task."""
    await task_service.delete_task(task_id, current_user.id)
