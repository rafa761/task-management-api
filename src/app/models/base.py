# app/models/base.py

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func


def utc_now() -> datetime:
    """Get current UTC time. Use this for all database operations."""
    return datetime.now(UTC)


class BaseModel(DeclarativeBase):
    """
    Base class for all database models.

    Provides common columns and functionality that all entities should have:
    - UUID primary key for security and scalability
    - Created/updated timestamps for audit trails
    - Proper timezone handling
    """

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True,
        comment="Unique identifier for the entity",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="When the entity was created (UTC)",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="When the entity was last updated (UTC)",
    )


class TimestampMixin:
    """
    Mixin for entities that need additional timestamp tracking.

    Useful for models that need more granular time tracking beyond
    the basic created_at/updated_at provided by Base.
    """

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the entity was soft deleted (null = active, UTC)",
    )

    @property
    def is_deleted(self) -> bool:
        """Check if the entity is soft deleted."""
        return self.deleted_at is not None

    def soft_delete(self) -> None:
        """Mark the entity as soft deleted with UTC timestamp."""
        self.deleted_at = utc_now()

    def restore(self) -> None:
        """Restore a soft deleted entity."""
        self.deleted_at = None


class AuditMixin:
    """
    Mixin for entities that need audit trail information.

    Tracks who created/modified entities for compliance and debugging.
    """

    created_by_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        nullable=True,
        comment="ID of the user who created the entity",
    )

    updated_by_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        nullable=True,
        comment="ID of the user who last updated this entity",
    )


class UserTimestampMixin:
    """
    Mixin for entities that need to track user-specific timestamps.

    Use this when you need to store timestamps that should be displayed
    in the user's timezone (like task due dates, meeting times, etc.)
    """

    user_created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Creation time in user's timezone",
    )

    user_timezone: Mapped[str | None] = mapped_column(
        nullable=True, comment="User's timezone when the entity was created"
    )
