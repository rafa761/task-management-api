# app/utils/dates.py
"""
Simple date utilities.
"""

from datetime import UTC, datetime, timedelta


def utc_now() -> datetime:
    """Current UTC time."""
    return datetime.now(UTC)


def yesterday() -> datetime:
    """Yesterday, same time."""
    return utc_now() - timedelta(days=1)


def tomorrow() -> datetime:
    """Tomorrow, same time."""
    return utc_now() + timedelta(days=1)


def days_ago(days: int) -> datetime:
    """N days ago."""
    return utc_now() - timedelta(days=days)


def days_from_now(days: int) -> datetime:
    """N days from now."""
    return utc_now() + timedelta(days=days)


def hours_ago(hours: int) -> datetime:
    """N hours ago."""
    return utc_now() - timedelta(hours=hours)


def hours_from_now(hours: int) -> datetime:
    """N hours from now."""
    return utc_now() + timedelta(hours=hours)
