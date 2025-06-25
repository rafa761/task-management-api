# app/models/user.py
"""
User model and related entities.

This module contains the User model and any user-specific functionality
including authentication, preferences, and profile management.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, utc_now

# Avoid circular imports with TYPE_CHECKING
if TYPE_CHECKING:
    from .task import Task, TaskAssignment
    from .team import TeamMembership


class User(Base, TimestampMixin):
    """
    User entity representing system users.

    Design Decisions:
    - UUID primary key for security (no enumerable IDs)
    - Email as unique identifier for authentication
    - Timezone storage for proper datetime handling
    - Soft delete support for data retention and audit compliance
    - Separate fields for display name vs authentication

    Security Considerations:
    - Password hashing handled by authentication service
    - Email verification required for account activation
    - Soft delete preserves audit trails
    """

    __tablename__ = "users"

    # Authentication and identification
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
        comment="User's email address (used for login)",
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="Bcrypt hashed password"
    )

    # Personal information
    first_name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="User's first name"
    )
    last_name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="User's last name"
    )

    # User preferences and settings
    timezone: Mapped[str] = mapped_column(
        String(50),
        default="UTC",
        nullable=False,
        comment="User's preferred timezone for date/time display",
    )

    # Account status and verification
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Whether the user account is active",
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether the user's email has been verified",
    )

    # Account lifecycle tracking
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the user last logged in (UTC)",
    )

    # Relationships (using string references to avoid circular imports)
    team_memberships: Mapped[list["TeamMembership"]] = relationship(
        "TeamMembership",
        back_populates="user",
        foreign_keys="TeamMembership.user_id",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    assigned_tasks: Mapped[list["TaskAssignment"]] = relationship(
        "TaskAssignment",
        back_populates="assignee",
        foreign_keys="TaskAssignment.assignee_id",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    created_tasks: Mapped[list["Task"]] = relationship(
        "Task",
        back_populates="creator",
        foreign_keys="Task.creator_id",
        passive_deletes=True,
    )

    # Properties and methods
    @property
    def full_name(self) -> str:
        """Get user's full name for display purposes."""
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def display_name(self) -> str:
        """Get user's display name (full name or email if name not available)."""
        full_name = self.full_name
        return full_name if full_name else self.email

    @property
    def initials(self) -> str:
        """Get user's initials for avatars."""
        if self.first_name and self.last_name:
            return f"{self.first_name[0]}{self.last_name[0]}".upper()
        if self.first_name:
            return self.first_name[0].upper()
        return self.email[0].upper()

    def update_last_login(self) -> None:
        """Update the last login timestamp."""
        self.last_login_at = utc_now()  # Use consistent UTC function

    def deactivate(self) -> None:
        """Deactivate the user account."""
        self.is_active = False
        self.soft_delete()  # From TimestampMixin

    def activate(self) -> None:
        """Activate the user account."""
        self.is_active = True
        self.restore()  # From TimestampMixin

    def verify_email(self) -> None:
        """Mark the user's email as verified."""
        self.is_verified = True

    def can_login(self) -> bool:
        """Check if user can log in (active and verified)."""
        return self.is_active and self.is_verified and not self.is_deleted

    def __repr__(self) -> str:
        return f"<User(id='{self.id}', email='{self.email}', name='{self.full_name}')>"
