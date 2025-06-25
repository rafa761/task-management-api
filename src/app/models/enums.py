# app/models/enums.py
"""
Centralized enum definitions for the application.

This module contains all enum types used across models, providing:
- Type safety at the Python level
- Database constraints at the PostgreSQL level
- Clear documentation of allowed values
- Easy maintenance of business rules
"""

import enum


class TeamRoleEnum(enum.Enum):
    """
    Team membership roles with hierarchical permissions.

    The hierarchy (highest to lowest):
    OWNER > ADMIN > MEMBER > VIEWER

    Permissions by role:
    - OWNER: Full control, can delete team, manage billing
    - ADMIN: Manage team settings, members, and all projects
    - MEMBER: Create and manage own tasks and projects
    - VIEWER: Read-only access to team content
    """

    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"

    @classmethod
    def admin_roles(cls) -> list["TeamRoleEnum"]:
        """Get roles that have administrative privileges."""
        return [cls.OWNER, cls.ADMIN]

    @classmethod
    def can_modify_team(cls, role: "TeamRoleEnum") -> bool:
        """Check if role can modify team settings."""
        return role in [cls.OWNER, cls.ADMIN]

    @classmethod
    def can_manage_members(cls, role: "TeamRoleEnum") -> bool:
        """Check if role can manage team members."""
        return role in [cls.OWNER, cls.ADMIN]


class TaskStatusEnum(enum.Enum):
    """
    Task lifecycle states representing workflow progression.

    Typical flow: TODO → IN_PROGRESS → IN_REVIEW → DONE
    Alternative: TODO → IN_PROGRESS → DONE (for simpler workflows)
    Exception: Any state → CANCELLED (for abandoned tasks)
    """

    TODO = "todo"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    DONE = "done"
    CANCELLED = "cancelled"

    @classmethod
    def active_statuses(cls) -> list["TaskStatusEnum"]:
        """Get statuses that represent active (not completed) tasks."""
        return [cls.TODO, cls.IN_PROGRESS, cls.IN_REVIEW]

    @classmethod
    def completed_statuses(cls) -> list["TaskStatusEnum"]:
        """Get statuses that represent completed tasks."""
        return [cls.DONE, cls.CANCELLED]

    def is_active(self) -> bool:
        """Check if this status represents an active task."""
        return self in self.active_statuses()

    def is_completed(self) -> bool:
        """Check if this status represents a completed task."""
        return self in self.completed_statuses()


class TaskPriorityEnum(enum.Enum):
    """
    Task priority levels for work prioritization.

    Priority guidelines:
    - URGENT: Critical issues, immediate attention required
    - HIGH: Important features, should be completed soon
    - MEDIUM: Standard priority, normal development flow
    - LOW: Nice-to-have features, can be delayed
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

    @classmethod
    def get_priority_order(cls) -> list["TaskPriorityEnum"]:
        """Get priorities in order from highest to lowest."""
        return [cls.URGENT, cls.HIGH, cls.MEDIUM, cls.LOW]

    def get_priority_score(self) -> int:
        """Get numeric score for priority (higher = more urgent)."""
        priority_scores = {
            self.URGENT: 4,
            self.HIGH: 3,
            self.MEDIUM: 2,
            self.LOW: 1,
        }
        return priority_scores[self]


class ProjectStatusEnum(enum.Enum):
    """
    Project lifecycle states for project management.

    States:
    - PLANNING: Project is being planned, not yet started
    - ACTIVE: Project is actively being worked on
    - ON_HOLD: Project is paused temporarily
    - COMPLETED: Project has been successfully completed
    - CANCELLED: Project has been cancelled or abandoned
    """

    PLANNING = "planning"
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

    @classmethod
    def active_statuses(cls) -> list["ProjectStatusEnum"]:
        """Get statuses representing active projects."""
        return [cls.PLANNING, cls.ACTIVE, cls.ON_HOLD]

    def is_active(self) -> bool:
        """Check if this status represents an active project."""
        return self in self.active_statuses()


class NotificationEventTypeEnum(enum.Enum):
    """
    Types of events that can trigger notifications.

    These events are used for:
    - Real-time notifications
    - Email notifications
    - Webhook events
    - Activity feeds
    """

    # Task events
    TASK_CREATED = "task_created"
    TASK_ASSIGNED = "task_assigned"
    TASK_STATUS_CHANGED = "task_status_changed"
    TASK_PRIORITY_CHANGED = "task_priority_changed"
    TASK_DUE_DATE_CHANGED = "task_due_date_changed"
    TASK_COMPLETED = "task_completed"
    TASK_DELETED = "task_deleted"

    # Team events
    TEAM_MEMBER_ADDED = "team_member_added"
    TEAM_MEMBER_REMOVED = "team_member_removed"
    TEAM_MEMBER_ROLE_CHANGED = "team_member_role_changed"

    # Project events
    PROJECT_CREATED = "project_created"
    PROJECT_STATUS_CHANGED = "project_status_changed"
    PROJECT_COMPLETED = "project_completed"

    # Comment events
    COMMENT_ADDED = "comment_added"
    COMMENT_MENTIONED = "comment_mentioned"


class AttachmentTypeEnum(enum.Enum):
    """
    Types of file attachments supported by the system.

    Used for:
    - File validation
    - Storage optimization
    - Security scanning priorities
    - UI rendering
    """

    # Documents
    PDF = "pdf"
    DOC = "doc"
    DOCX = "docx"
    TXT = "txt"

    # Images
    PNG = "png"
    JPG = "jpg"
    JPEG = "jpeg"
    GIF = "gif"
    SVG = "svg"

    # Spreadsheets
    XLS = "xls"
    XLSX = "xlsx"
    CSV = "csv"

    # Other
    ZIP = "zip"
    JSON = "json"

    @classmethod
    def image_types(cls) -> list["AttachmentTypeEnum"]:
        """Get attachment types that are images."""
        return [cls.PNG, cls.JPG, cls.JPEG, cls.GIF, cls.SVG]

    @classmethod
    def document_types(cls) -> list["AttachmentTypeEnum"]:
        """Get attachment types that are documents."""
        return [cls.PDF, cls.DOC, cls.DOCX, cls.TXT]

    def is_image(self) -> bool:
        """Check if this attachment type is an image."""
        return self in self.image_types()
