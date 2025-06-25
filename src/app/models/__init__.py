# app/models/__init__.py
"""
Models package for the Task Management API.

This module provides a clean interface to all database models and related
components for easy importing throughout the application.

Usage:
    from app.models import UserModel, TeamModel, TaskModel, TeamRoleEnum, TaskStatusEnum
    from app.models import Base  # For migrations and database operations

The models are organized by domain:
- user.py: User authentication and profile models
- team.py: Team and membership models
- project.py: Project organization models
- task.py: Task, assignment, and dependency models
- enums.py: Shared enum definitions
- base.py: Base model class and mixins
"""

from .base import AuditMixin, BaseModel, TimestampMixin, UserTimestampMixin

# Import all enum types
from .enums import (
    AttachmentTypeEnum,
    NotificationEventTypeEnum,
    ProjectStatusEnum,
    TaskPriorityEnum,
    TaskStatusEnum,
    TeamRoleEnum,
)
from .project import ProjectModel
from .task import TaskAssignmentModel, TaskDependencyModel, TaskModel
from .team import TeamMembershipModel, TeamModel

# Import model classes in dependency order
from .user import UserModel

# Export all models and components for easy importing
__all__ = [
    # Base components
    "BaseModel",
    "TimestampMixin",
    "AuditMixin",
    "UserTimestampMixin",
    # Enums
    "TeamRoleEnum",
    "TaskStatusEnum",
    "TaskPriorityEnum",
    "ProjectStatusEnum",
    "NotificationEventTypeEnum",
    "AttachmentTypeEnum",
    # Models
    "UserModel",
    "TeamModel",
    "TeamMembershipModel",
    "ProjectModel",
    "TaskModel",
    "TaskAssignmentModel",
    "TaskDependencyModel",
]
