# app/models/task.py
"""
Task models including assignments and dependencies.

This module contains the core task management entities:
- Task: Core work items with rich metadata
- TaskAssignment: User-task assignment relationships
- TaskDependency: Task dependency and blocking relationships
"""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from .base import Base, TimestampMixin, utc_now
from .enums import TaskPriorityEnum, TaskStatusEnum

# Avoid circular imports
if TYPE_CHECKING:
    from .project import Project
    from .team import Team
    from .user import User


class Task(Base, TimestampMixin):
    """
    Core Task entity with rich metadata and relationships.

    Design Decisions:
    - Belongs to team for multi-tenancy (required)
    - Optional project association for flexibility
    - Creator vs assignee distinction for audit trails
    - Priority and status enums for type safety and DB constraints
    - Position field for custom task ordering
    - Due date support for deadline management
    - Soft delete to preserve task history

    Task Lifecycle:
    1. Created by a user (creator_id)
    2. Optionally assigned to one or more users (via TaskAssignment)
    3. Status transitions through workflow (TODO → IN_PROGRESS → DONE)
    4. Can be blocked by dependencies (via TaskDependency)
    """

    __tablename__ = "tasks"

    # Required relationships
    team_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Team that owns this task (multi-tenant boundary)",
    )
    creator_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="User who created this task",
    )

    # Optional relationships
    project_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Optional project this task belongs to",
    )

    # Core task information
    title: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="Task title/summary"
    )
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Detailed task description and requirements"
    )

    # Task metadata and workflow
    status: Mapped[TaskStatusEnum] = mapped_column(
        Enum(TaskStatusEnum),
        default=TaskStatusEnum.TODO,
        nullable=False,
        index=True,
        comment="Current task status in workflow",
    )
    priority: Mapped[TaskPriorityEnum] = mapped_column(
        Enum(TaskPriorityEnum),
        default=TaskPriorityEnum.MEDIUM,
        nullable=False,
        index=True,
        comment="Task priority level",
    )

    # Timeline and deadlines
    due_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True, comment="Task deadline"
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="When the task was completed"
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="When work on the task began"
    )

    # Task organization and display
    position: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Display order within project/team task lists",
    )

    # Effort estimation
    estimated_hours: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Estimated effort in hours"
    )
    actual_hours: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Actual time spent in hours"
    )

    # Task settings
    is_archived: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether task is archived (hidden from active views)",
    )

    # Relationships
    team: Mapped["Team"] = relationship("Team")
    project: Mapped["Project"] = relationship("Project", back_populates="tasks")
    creator: Mapped["User"] = relationship(
        "User", back_populates="created_tasks", foreign_keys=[creator_id]
    )

    # Many-to-many relationships through association objects
    assignments: Mapped[list["TaskAssignment"]] = relationship(
        "TaskAssignment",
        back_populates="task",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    # Task dependencies (tasks this task depends on)
    dependencies: Mapped[list["TaskDependency"]] = relationship(
        "TaskDependency",
        back_populates="dependent_task",
        foreign_keys="TaskDependency.dependent_task_id",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    # Tasks that depend on this task
    dependents: Mapped[list["TaskDependency"]] = relationship(
        "TaskDependency",
        foreign_keys="TaskDependency.prerequisite_task_id",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    # Properties and computed fields
    @property
    def is_overdue(self) -> bool:
        """Check if task is past its due date."""
        if not self.due_date or self.status.is_completed():
            return False
        return utc_now() > self.due_date

    @property
    def days_until_due(self) -> int | None:
        """Calculate days until due date."""
        if not self.due_date:
            return None
        delta = self.due_date - utc_now()
        return delta.days

    @property
    def assignee_ids(self) -> list[UUID]:
        """Get list of assigned user IDs."""
        return [assignment.assignee_id for assignment in self.assignments]

    @property
    def is_blocked(self) -> bool:
        """Check if task is blocked by incomplete dependencies."""
        return any(
            not dep.prerequisite_task.status.is_completed() for dep in self.dependencies
        )

    @property
    def blocking_tasks_count(self) -> int:
        """Count how many tasks this task is blocking."""
        return len(
            [
                dep
                for dep in self.dependents
                if not dep.dependent_task.status.is_completed()
            ]
        )

    # Status management methods
    def start_task(self, user_id: UUID | None = None) -> None:
        """Start working on the task."""
        if self.status == TaskStatusEnum.TODO:
            self.status = TaskStatusEnum.IN_PROGRESS
            self.started_at = utc_now()

            # Auto-assign to the user who started it if not already assigned
            if user_id and not self.assignee_ids:
                self.assign_to_user(user_id)

    def complete_task(self) -> None:
        """Mark the task as completed."""
        self.status = TaskStatusEnum.DONE
        self.completed_at = utc_now()

    def cancel_task(self) -> None:
        """Cancel the task."""
        self.status = TaskStatusEnum.CANCELLED
        self.completed_at = utc_now()

    def reopen_task(self) -> None:
        """Reopen a completed or cancelled task."""
        if self.status.is_completed():
            self.status = TaskStatusEnum.TODO
            self.completed_at = None
            self.started_at = None

    def set_priority(self, priority: TaskPriorityEnum) -> None:
        """Change task priority."""
        self.priority = priority

    # Assignment management
    def assign_to_user(self, user_id: UUID) -> "TaskAssignment":
        """Assign task to a user."""
        # Check if already assigned
        existing = next((a for a in self.assignments if a.assignee_id == user_id), None)
        if existing:
            return existing

        # Create new assignment
        assignment = TaskAssignment(task_id=self.id, assignee_id=user_id)
        self.assignments.append(assignment)
        return assignment

    def unassign_from_user(self, user_id: UUID) -> bool:
        """Remove user assignment from task."""
        assignment = next(
            (a for a in self.assignments if a.assignee_id == user_id), None
        )
        if assignment:
            self.assignments.remove(assignment)
            return True
        return False

    def is_assigned_to(self, user_id: UUID) -> bool:
        """Check if task is assigned to a specific user."""
        return user_id in self.assignee_ids

    # Dependency management
    def add_dependency(self, prerequisite_task: "Task") -> "TaskDependency":
        """Add a task dependency."""
        # Prevent self-dependency
        if prerequisite_task.id == self.id:
            raise ValueError("Task cannot depend on itself")

        # Check if dependency already exists
        existing = next(
            (
                d
                for d in self.dependencies
                if d.prerequisite_task_id == prerequisite_task.id
            ),
            None,
        )
        if existing:
            return existing

        # Create new dependency
        dependency = TaskDependency(
            dependent_task_id=self.id, prerequisite_task_id=prerequisite_task.id
        )
        self.dependencies.append(dependency)
        return dependency

    def remove_dependency(self, prerequisite_task_id: UUID) -> bool:
        """Remove a task dependency."""
        dependency = next(
            (
                d
                for d in self.dependencies
                if d.prerequisite_task_id == prerequisite_task_id
            ),
            None,
        )
        if dependency:
            self.dependencies.remove(dependency)
            return True
        return False

    # Archive management
    def archive(self) -> None:
        """Archive the task."""
        self.is_archived = True

    def unarchive(self) -> None:
        """Unarchive the task."""
        self.is_archived = False

    def __repr__(self) -> str:
        return (
            f"<Task(id='{self.id}', title='{self.title}', "
            f"status='{self.status.value}', team_id='{self.team_id}')>"
        )


class TaskAssignment(Base):
    """
    Task assignment tracking who is working on what.

    Design Decisions:
    - Many-to-many relationship between tasks and users
    - Assignment timestamp for audit trails
    - Supports multiple assignees per task
    - Simple model focused on assignment tracking

    Assignment Workflow:
    1. User is assigned to task (assignment created)
    2. Assignment timestamp records when assignment occurred
    3. Assignment can be removed (record deleted)
    """

    __tablename__ = "task_assignments"

    # Foreign key relationships
    task_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        comment="Task being assigned",
    )
    assignee_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="User assigned to the task",
    )

    # Assignment metadata
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="When the assignment was made",
    )
    assigned_by_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
        comment="User who made the assignment",
    )

    # Relationships
    task: Mapped[Task] = relationship("Task", back_populates="assignments")
    assignee: Mapped["User"] = relationship(
        "User", back_populates="assigned_tasks", foreign_keys=[assignee_id]
    )
    assigned_by: Mapped["User | None"] = relationship(
        "User", foreign_keys=[assigned_by_id]
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint("task_id", "assignee_id", name="unique_task_assignment"),
    )

    def __repr__(self) -> str:
        return (
            f"<TaskAssignment(task_id='{self.task_id}', "
            f"assignee_id='{self.assignee_id}')>"
        )


class TaskDependency(Base):
    """
    Task dependency relationships for workflow management.

    Design Decisions:
    - Self-referential many-to-many on tasks
    - Simple blocking relationship (prerequisite must complete first)
    - Circular dependency prevention (enforced at application level)
    - Dependency type can be extended in future for different relationships

    Dependency Logic:
    - dependent_task cannot start until prerequisite_task is completed
    - Supports complex workflow management and critical path analysis
    - Enables automatic task unblocking when prerequisites complete
    """

    __tablename__ = "task_dependencies"

    # Self-referential foreign keys
    dependent_task_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        comment="Task that depends on another task",
    )
    prerequisite_task_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        comment="Task that must be completed first",
    )

    # Dependency metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="When the dependency was created",
    )
    created_by_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
        comment="User who created the dependency",
    )

    # Relationships
    dependent_task: Mapped[Task] = relationship(
        "Task", back_populates="dependencies", foreign_keys=[dependent_task_id]
    )
    prerequisite_task: Mapped[Task] = relationship(
        "Task", foreign_keys=[prerequisite_task_id]
    )
    created_by: Mapped["User | None"] = relationship(
        "User", foreign_keys=[created_by_id]
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint(
            "dependent_task_id", "prerequisite_task_id", name="unique_task_dependency"
        ),
        CheckConstraint(
            "dependent_task_id != prerequisite_task_id", name="no_self_dependency"
        ),
    )

    @property
    def is_blocking(self) -> bool:
        """Check if this dependency is currently blocking the dependent task."""
        return not self.prerequisite_task.status.is_completed()

    def __repr__(self) -> str:
        return (
            f"<TaskDependency(dependent='{self.dependent_task_id}', "
            f"prerequisite='{self.prerequisite_task_id}')>"
        )
