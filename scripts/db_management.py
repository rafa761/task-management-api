"""
Database management utilities for development and deployment.

This script provides common database operations like creating migrations,
applying migrations, and resetting the database.
"""

import asyncio
import sys
from pathlib import Path

import typer
from alembic import command
from alembic.config import Config

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.config import settings
from app.core.database import db_config

app = typer.Typer(help="Database management commands")


def get_alembic_config() -> Config:
    """Get Alembic configuration."""
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", settings.database_url)
    return alembic_cfg


@app.command()
def create_migration(message: str = typer.Argument(..., help="Migration message")):
    """Create a new database migration."""
    typer.echo(f"Creating migration: {message}")
    alembic_cfg = get_alembic_config()
    command.revision(alembic_cfg, message=message, autogenerate=True)
    typer.echo("Migration created successfully!")


@app.command()
def migrate(revision: str = typer.Argument("head", help="Target revision")):
    """Apply database migrations."""
    typer.echo(f"Applying migrations to: {revision}")
    alembic_cfg = get_alembic_config()
    command.upgrade(alembic_cfg, revision)
    typer.echo("Migrations applied successfully!")


@app.command()
def downgrade(revision: str = typer.Argument("-1", help="Target revision")):
    """Downgrade database migrations."""
    typer.echo(f"Downgrading to: {revision}")
    alembic_cfg = get_alembic_config()
    command.downgrade(alembic_cfg, revision)
    typer.echo("Downgrade completed successfully!")


@app.command()
def current():
    """Show current migration revision."""
    alembic_cfg = get_alembic_config()
    command.current(alembic_cfg)


@app.command()
def history():
    """Show migration history."""
    alembic_cfg = get_alembic_config()
    command.history(alembic_cfg)


@app.command()
def reset_db():
    """Reset database (drop and recreate all tables)."""
    if not typer.confirm("This will delete all data. Are you sure?"):
        typer.echo("Aborted.")
        return

    async def _reset():
        await db_config.initialize_database(drop_existing=True)
        typer.echo("Database reset completed!")

    asyncio.run(_reset())


@app.command()
def init_db():
    """Initialize database with initial schema."""

    async def _init():
        await db_config.initialize_database(drop_existing=False)
        typer.echo("Database initialized!")

    asyncio.run(_init())


@app.command()
def check_health():
    """Check database connection health."""
    from app.core.database import check_database_health

    async def _check():
        health = await check_database_health()
        if health["status"] == "healthy":
            typer.echo("✅ Database is healthy")
        else:
            typer.echo(f"❌ Database health check failed: {health['message']}")
            sys.exit(1)

    asyncio.run(_check())


if __name__ == "__main__":
    app()
