# app/models/project.py
"""
Project model for organizing tasks within teams.

This module handles project management including:
- Project entity for grouping related tasks
- Project timeline and status tracking
- Team-scoped project organization
"""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    Boolean,
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

from .base import Base, TimestampMixin, utc_now
from .enums import ProjectStatusEnum

# Avoid circular imports
if TYPE_CHECKING:
    from .task import Task
    from .team import Team


class Project(Base, TimestampMixin):
    """
    Project entity for grouping tasks within teams.

    Design Decisions:
    - Optional but valuable for task organization and planning
    - Belongs to exactly one team for multi-tenant isolation
    - Timeline support with start/end dates for project planning
    - Status tracking for project lifecycle management
    - Soft delete to preserve project history and audit trails

    Project Organization Pattern:
    - Teams can have multiple projects
    - Tasks can optionally belong to a project
    - Projects provide additional context and grouping for related work
    - Project completion can be tracked independently of individual tasks
    """

    __tablename__ = "projects"

    # Team relationship (required)
    team_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Team that owns this project",
    )

    # Basic project information
    name: Mapped[str] = mapped_column(
        String(200), nullable=False, comment="Project name"
    )
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Detailed project description and goals"
    )

    # Project status and lifecycle
    status: Mapped[ProjectStatusEnum] = mapped_column(
        Enum(ProjectStatusEnum),
        default=ProjectStatusEnum.PLANNING,
        nullable=False,
        comment="Current project status",
    )

    # Project timeline
    start_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Planned or actual project start date",
    )
    end_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Planned or actual project end date",
    )

    # Project settings
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, comment="Whether the project is active"
    )

    # Project organization
    color: Mapped[str | None] = mapped_column(
        String(7),  # Hex color code (#RRGGBB)
        nullable=True,
        comment="Project color for UI display (hex code)",
    )

    position: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, comment="Display order within team projects"
    )

    # Progress tracking
    estimated_hours: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Estimated project duration in hours"
    )

    # Relationships
    team: Mapped["Team"] = relationship("Team", back_populates="projects")

    tasks: Mapped[list["Task"]] = relationship(
        "Task",
        back_populates="project",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Task.position, Task.created_at",
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint(
            "team_id",
            "name",
            name="unique_team_project_name",
            sqlite_on_conflict="REPLACE",  # For SQLite compatibility in tests
        ),
    )

    # Properties and computed fields
    @property
    def is_overdue(self) -> bool:
        """Check if project is past its end date."""
        if not self.end_date:
            return False
        return self.status.is_active() and utc_now() > self.end_date

    @property
    def duration_days(self) -> int | None:
        """Calculate project duration in days."""
        if not self.start_date or not self.end_date:
            return None
        return (self.end_date - self.start_date).days

    @property
    def days_remaining(self) -> int | None:
        """Calculate days remaining until project end date."""
        if not self.end_date or not self.status.is_active():
            return None
        remaining = (self.end_date - utc_now()).days
        return max(0, remaining)

    @property
    def completion_percentage(self) -> float:
        """Calculate project completion based on task completion."""
        if not self.tasks:
            return 0.0

        completed_tasks = sum(1 for task in self.tasks if task.status.is_completed())
        return (completed_tasks / len(self.tasks)) * 100

    # Status management methods
    def start_project(self) -> None:
        """Start the project (set status to ACTIVE)."""
        self.status = ProjectStatusEnum.ACTIVE
        if not self.start_date:
            self.start_date = utc_now()

    def complete_project(self) -> None:
        """Complete the project."""
        self.status = ProjectStatusEnum.COMPLETED
        if not self.end_date:
            self.end_date = utc_now()

    def cancel_project(self) -> None:
        """Cancel the project."""
        self.status = ProjectStatusEnum.CANCELLED
        self.is_active = False

    def put_on_hold(self) -> None:
        """Put the project on hold."""
        self.status = ProjectStatusEnum.ON_HOLD

    def resume_project(self) -> None:
        """Resume a project from hold."""
        if self.status == ProjectStatusEnum.ON_HOLD:
            self.status = ProjectStatusEnum.ACTIVE

    # Task management helpers
    def get_active_tasks(self) -> list["Task"]:
        """Get all active (non-completed) tasks in this project."""
        return [task for task in self.tasks if task.status.is_active()]

    def get_completed_tasks(self) -> list["Task"]:
        """Get all completed tasks in this project."""
        return [task for task in self.tasks if task.status.is_completed()]

    def get_overdue_tasks(self) -> list["Task"]:
        """Get all overdue tasks in this project."""
        now = utc_now()
        return [
            task
            for task in self.tasks
            if (task.due_date and task.due_date < now and task.status.is_active())
        ]

    # Timeline validation
    def validate_timeline(self) -> bool:
        """Validate that start_date is before end_date."""
        if self.start_date and self.end_date:
            return self.start_date <= self.end_date
        return True

    def __repr__(self) -> str:
        return (
            f"<Project(id='{self.id}', name='{self.name}', "
            f"status='{self.status.value}', team_id='{self.team_id}')>"
        )
