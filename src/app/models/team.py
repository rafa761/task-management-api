# app/models/team.py
"""
Team and team membership models.

This module handles team/workspace management including:
- Team entity for multi-tenant organization
- TeamMembership for user-team relationships with roles
- Team-level settings and preferences
"""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel, TimestampMixin, utc_now
from .enums import TeamRoleEnum

# Avoid circular imports
if TYPE_CHECKING:
    from .project import ProjectModel
    from .user import UserModel


class TeamModel(BaseModel, TimestampMixin):
    """
    Team/Workspace entity for multi-tenant organization.

    Design Decisions:
    - Teams are the primary tenant boundary for data isolation
    - Unique slug for user-friendly URLs (e.g., /teams/acme-corp)
    - Soft delete to preserve audit trails and prevent data loss
    - Team settings can be extended for customization

    Multi-Tenancy Pattern:
    - All business data (projects, tasks) belongs to a team
    - Users can be members of multiple teams
    - Team membership determines access permissions
    """

    __tablename__ = "teams"

    # Basic team information
    name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="Human-readable team name"
    )
    slug: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
        comment="URL-friendly team identifier (e.g., 'acme-corp')",
    )
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Optional team description or purpose"
    )

    # Team settings and preferences
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Whether the team is active (for billing/access control)",
    )

    # Team customization settings
    allow_public_signup: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether users can join this team without invitation",
    )

    default_task_priority: Mapped[str] = mapped_column(
        String(20),
        default="medium",
        nullable=False,
        comment="Default priority for new tasks in this team",
    )

    # Relationships
    memberships: Mapped[list["TeamMembershipModel"]] = relationship(
        "TeamMembershipModel",
        back_populates="team",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    projects: Mapped[list["ProjectModel"]] = relationship(
        "ProjectModel",
        back_populates="team",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    # Helper methods
    def get_owners(self) -> list["TeamMembershipModel"]:
        """Get all team owners."""
        return [m for m in self.memberships if m.role == TeamRoleEnum.OWNER]

    def get_admins(self) -> list["TeamMembershipModel"]:
        """Get all team admins (owners + admins)."""
        return [m for m in self.memberships if m.role in TeamRoleEnum.admin_roles()]

    def get_active_members(self) -> list["TeamMembershipModel"]:
        """Get all active team members (joined and not deleted)."""
        return [
            m for m in self.memberships if m.joined_at is not None and not m.is_deleted
        ]

    def member_count(self) -> int:
        """Get count of active members."""
        return len(self.get_active_members())

    def has_member(self, user_id: UUID) -> bool:
        """Check if a user is an active member of this team."""
        return any(
            m.user_id == user_id and m.joined_at is not None and not m.is_deleted
            for m in self.memberships
        )

    def get_member_role(self, user_id: UUID) -> TeamRoleEnum | None:
        """Get a user's role in this team."""
        for membership in self.memberships:
            if (
                membership.user_id == user_id
                and membership.joined_at is not None
                and not membership.is_deleted
            ):
                return membership.role
        return None

    def can_user_modify(self, user_id: UUID) -> bool:
        """Check if a user can modify this team."""
        role = self.get_member_role(user_id)
        return role is not None and TeamRoleEnum.can_modify_team(role)

    def __repr__(self) -> str:
        return f"<TeamModel(id='{self.id}', name='{self.name}', slug='{self.slug}')>"


class TeamMembershipModel(BaseModel):
    """
    Many-to-many relationship between Users and Teams with rich metadata.

    Design Decisions:
    - Separate entity instead of simple many-to-many for rich relationship data
    - Role-based access control with hierarchical permissions
    - Invitation workflow tracking (invited_at vs joined_at)
    - Audit trail for membership changes

    Invitation Workflow:
    1. User is invited (membership created with invited_at, no joined_at)
    2. User accepts invitation (joined_at is set)
    3. User can be deactivated (soft delete) without losing history
    """

    __tablename__ = "team_memberships"

    # Foreign key relationships
    user_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="User who is a member of the team",
    )
    team_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False,
        comment="Team that the user belongs to",
    )

    # Role and permissions
    role: Mapped[TeamRoleEnum] = mapped_column(
        Enum(TeamRoleEnum),
        default=TeamRoleEnum.MEMBER,
        nullable=False,
        comment="User's role and permissions within the team",
    )

    # Membership lifecycle
    invited_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="When the user was invited to the team",
    )
    joined_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the user accepted the invitation (null = pending)",
    )

    # Invitation metadata
    invited_by_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
        comment="User who sent the invitation",
    )

    # Soft delete for membership history
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the membership was deactivated",
    )

    # Relationships
    user: Mapped["UserModel"] = relationship(
        "UserModel", back_populates="team_memberships", foreign_keys=[user_id]
    )
    team: Mapped[TeamModel] = relationship("TeamModel", back_populates="memberships")
    invited_by: Mapped["UserModel"] = relationship(
        "UserModel", foreign_keys=[invited_by_id]
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "team_id",
            name="unique_user_team_membership",
            sqlite_on_conflict="REPLACE",  # For SQLite compatibility in tests
        ),
    )

    # Properties and methods
    @property
    def is_pending(self) -> bool:
        """Check if the membership invitation is still pending."""
        return self.joined_at is None and self.deleted_at is None

    @property
    def is_active(self) -> bool:
        """Check if the membership is active (joined and not deleted)."""
        return self.joined_at is not None and self.deleted_at is None

    @property
    def is_deleted(self) -> bool:
        """Check if the membership has been deactivated."""
        return self.deleted_at is not None

    def accept_invitation(self) -> None:
        """Accept the team invitation."""
        if self.is_pending:
            self.joined_at = utc_now()  # Use consistent UTC function

    def deactivate(self) -> None:
        """Deactivate the membership (soft delete)."""
        self.deleted_at = utc_now()  # Use consistent UTC function

    def reactivate(self) -> None:
        """Reactivate a deactivated membership."""
        self.deleted_at = None

    def change_role(self, new_role: TeamRoleEnum) -> None:
        """Change the user's role in the team."""
        self.role = new_role

    def has_permission(self, required_role: TeamRoleEnum) -> bool:
        """Check if this membership has at least the required role level."""
        if not self.is_active:
            return False

        role_hierarchy = {
            TeamRoleEnum.VIEWER: 1,
            TeamRoleEnum.MEMBER: 2,
            TeamRoleEnum.ADMIN: 3,
            TeamRoleEnum.OWNER: 4,
        }

        current_level = role_hierarchy.get(self.role, 0)
        required_level = role_hierarchy.get(required_role, 0)

        return current_level >= required_level

    def can_manage_team(self) -> bool:
        """Check if this membership can manage team settings."""
        return self.is_active and TeamRoleEnum.can_modify_team(self.role)

    def can_manage_members(self) -> bool:
        """Check if this membership can manage other team members."""
        return self.is_active and TeamRoleEnum.can_manage_members(self.role)

    def __repr__(self) -> str:
        status = (
            "pending" if self.is_pending else "active" if self.is_active else "deleted"
        )
        return (
            f"<TeamMembershipModel(user_id='{self.user_id}', team_id='{self.team_id}', "
            f"role='{self.role.value}', status='{status}')>"
        )
