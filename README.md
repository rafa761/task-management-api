# team-task-management-api

Portfolio project to show some important backend concepts

Install dev requirements

```bash
pip install -r requirements-dev.txt
```

Install pre commit hooks

```bash
pre-commit install
```

Alembic database version control

Create revision

```bash
alembic revision --autogenerate -m "Initial migration with all models"
```

# Apply all pending migrations

```bash
alembic upgrade head
```

# Or apply to a specific revision

```bash
alembic upgrade abc123
```

# Show current revision

```bash
alembic current
```

# Show migration history

```bash
alembic history --verbose
```

# Show pending migrations

```bash
alembic heads
```

# Downgrade one step

```bash
alembic downgrade -1
```
