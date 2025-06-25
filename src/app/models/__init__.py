# app/models/__init__.py
"""
Models package for the Task Management API.

This module provides a clean interface to all database models and related
components for easy importing throughout the application.

Usage:
    from app.models import User, Team, Task, TeamRoleEnum, TaskStatusEnum
    from app.models import Base  # For migrations and database operations

The models are organized by domain:
- user.py: User authentication and profile models
- team.py: Team and membership models
- project.py: Project organization models
- task.py: Task, assignment, and dependency models
- enums.py: Shared enum definitions
- base.py: Base model class and mixins
"""

from .base import AuditMixin, Base, TimestampMixin, UserTimestampMixin, utc_now

# Import all enum types
from .enums import (
    AttachmentTypeEnum,
    NotificationEventTypeEnum,
    ProjectStatusEnum,
    TaskPriorityEnum,
    TaskStatusEnum,
    TeamRoleEnum,
)
from .project import Project
from .task import Task, TaskAssignment, TaskDependency
from .team import Team, TeamMembership

# Import model classes in dependency order
from .user import User

# Export all models and components for easy importing
__all__ = [
    # Base components
    "Base",
    "TimestampMixin",
    "AuditMixin",
    "UserTimestampMixin",
    "utc_now",
    # Enums
    "TeamRoleEnum",
    "TaskStatusEnum",
    "TaskPriorityEnum",
    "ProjectStatusEnum",
    "NotificationEventTypeEnum",
    "AttachmentTypeEnum",
    # Models
    "User",
    "Team",
    "TeamMembership",
    "Project",
    "Task",
    "TaskAssignment",
    "TaskDependency",
]
