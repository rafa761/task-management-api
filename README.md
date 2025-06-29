# Task Management API

A modern, async FastAPI-based task management system built with PostgreSQL and comprehensive testing.

## Features

- **User Management** - Registration, authentication, and profile management
- **Task Organization** - Create, update, and track tasks with status management
- **JWT Authentication** - Secure access and refresh token implementation
- **Async Database** - High-performance PostgreSQL with SQLAlchemy async
- **Comprehensive Testing** - Full test coverage with pytest and async support

## Tech Stack

- **FastAPI** - Modern, fast web framework for building APIs
- **PostgreSQL** - Robust relational database with async support
- **SQLAlchemy** - Powerful ORM with async capabilities
- **Pydantic** - Data validation and settings management
- **JWT** - Secure authentication tokens
- **Pytest** - Comprehensive testing framework

## System Design

[System Design Doc](https://github.com/rafa761/team-task-management-api/blob/develop/docs/system-design.md)

## Quick Start

1. **Install dependencies**

   ```bash
   pip install -r requirements-dev.txt
   pre-commit install
   ```

2. **Setup database**

   ```bash
   # Configure your database connection in .env
   cp .example.env .env

   # Run migrations
   alembic upgrade head
   ```

3. **Run the application**

   ```bash
   uvicorn src.app.main:app --reload
   ```

4. **Run tests**
   ```bash
   pytest
   ```

## API Documentation

Once running, visit:

- **Interactive API docs**: http://localhost:8000/docs
- **Alternative docs**: http://localhost:8000/redoc

![OpenApiDoc1](/docs/images/openapi-doc-1.png)

![OpenApiDoc2](/docs/images/openapi-doc-2.png)

![OpenApiDoc3](/docs/images/openapi-doc-3.png)

## Development

- **Code quality**: `ruff check . && ruff format .`
- **Run all checks**: `pre-commit run --all-files`

## Project Structure

```
src/app/
   ├──core/          # Configuration and database setup
   ├──models/        # SQLAlchemy database models
   ├──schemas/       # Pydantic request/response models
   ├──repositories/  # Data access layer
   ├──services/      # Business logic layer
   ├──routers/       # API route handlers
   └──utils/         # Shared utilities
```

---

_This is a portfolio project demonstrating modern Python API development practices._
