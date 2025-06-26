# Task Management API - System Design

## Overview

A RESTful API for task management built with **FastAPI**, implementing **Clean Architecture** principles with **Repository Pattern**. The system provides user authentication via JWT tokens and full CRUD operations for task management.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                             │
├─────────────────────────────────────────────────────────────────┤
│  Web Browser  │  Mobile App  │  Third-party Apps  │  CLI Tool  │
└─────────────────────────────────────────────────────────────────┘
                                   │
                                   │ HTTP/HTTPS
                                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                     PRESENTATION LAYER                          │
├─────────────────────────────────────────────────────────────────┤
│                       FastAPI Router                            │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐              │
│  │ Auth Router │ │User Router  │ │Task Router  │              │
│  └─────────────┘ └─────────────┘ └─────────────┘              │
└─────────────────────────────────────────────────────────────────┘
                                   │
                                   │ Dependency Injection
                                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                      BUSINESS LAYER                             │
├─────────────────────────────────────────────────────────────────┤
│                        Services                                 │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐              │
│  │AuthService  │ │UserService  │ │TaskService  │              │
│  └─────────────┘ └─────────────┘ └─────────────┘              │
└─────────────────────────────────────────────────────────────────┘
                                   │
                                   │ Repository Interface
                                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                     PERSISTENCE LAYER                           │
├─────────────────────────────────────────────────────────────────┤
│                      Repositories                               │
│  ┌─────────────────┐ ┌─────────────────┐                      │
│  │ UserRepository  │ │ TaskRepository  │                      │
│  └─────────────────┘ └─────────────────┘                      │
└─────────────────────────────────────────────────────────────────┘
                                   │
                                   │ SQLAlchemy ORM
                                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                       DATA LAYER                                │
├─────────────────────────────────────────────────────────────────┤
│                    PostgreSQL Database                          │
│  ┌─────────────┐ ┌─────────────┐                              │
│  │   Users     │ │    Tasks    │                              │
│  │   Table     │ │    Table    │                              │
│  └─────────────┘ └─────────────┘                              │
└─────────────────────────────────────────────────────────────────┘
```

## Project Structure

```
task-management-api/
├── app/
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py          # Application settings
│   │   ├── database.py        # Database configuration
│   │   └── factory.py         # FastAPI app factory
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py           # Base model class
│   │   ├── user.py           # User SQLAlchemy model
│   │   └── task.py           # Task SQLAlchemy model
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── auth.py           # Authentication Pydantic schemas
│   │   ├── user.py           # User Pydantic schemas
│   │   └── task.py           # Task Pydantic schemas
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── base_repository.py # Abstract base repository
│   │   ├── user_repository.py # User data access layer
│   │   └── task_repository.py # Task data access layer
│   ├── services/
│   │   ├── __init__.py
│   │   ├── auth_service.py    # Authentication business logic
│   │   ├── user_service.py    # User business logic
│   │   └── task_service.py    # Task business logic
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── auth.py           # Authentication endpoints
│   │   ├── users.py          # User management endpoints
│   │   └── tasks.py          # Task management endpoints
│   └── dependencies.py       # Dependency injection setup
├── tests/
│   ├── conftest.py           # Pytest configuration
│   ├── test_models.py        # Database models tests
│   ├── test_repositories.py  # Repository tests
│   └── test_routers.py       # Routers tests
├── main.py                   # Application entry point
├── requirements.txt          # Project dependencies
└── README.md                # Project documentation
```

## Core Components

### 1. **Models (Data Layer)**

- **BaseModel**: Common fields and functionality for all models
- **User**: User entity with authentication fields
- **Task**: Task entity with relationship to User

### 2. **Repositories (Data Access Layer)**

- **BaseRepository**: Generic CRUD operations
- **UserRepository**: User-specific database operations
- **TaskRepository**: Task-specific database operations with ownership validation

### 3. **Services (Business Logic Layer)**

- **AuthService**: JWT token management, password hashing, user authentication
- **UserService**: User management business rules
- **TaskService**: Task management business rules with ownership validation

### 4. **Routers (Presentation Layer)**

- **AuthRouter**: Authentication endpoints (register, login, refresh)
- **UsersRouter**: User profile management
- **TasksRouter**: CRUD operations for tasks

## Data Models

### User Model

```python
User {
    id: UUID (PK)
    email: str (unique)
    username: str (unique)
    full_name: str
    hashed_password: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    tasks: List[Task] (relationship)
}
```

### Task Model

```python
Task {
    id: UUID (PK)
    title: str
    description: str (optional)
    status: TaskStatus (todo, in_progress, completed)
    priority: TaskPriority (low, medium, high)
    due_date: datetime (optional)
    owner_id: UUID (FK -> User.id)
    created_at: datetime
    updated_at: datetime
    owner: User (relationship)
}
```

## Security Architecture

### Authentication Flow

```
1. User Registration
   ├── Validate input data
   ├── Check email/username uniqueness
   ├── Hash password with bcrypt
   └── Store user in database

2. User Login
   ├── Validate credentials
   ├── Verify password hash
   ├── Generate JWT access token
   ├── Generate JWT refresh token
   └── Return tokens to client

3. Protected Endpoint Access
   ├── Extract Bearer token from header
   ├── Validate JWT signature
   ├── Check token expiration
   ├── Extract user information
   └── Proceed with request
```

### Security Features

- **Password Hashing**: bcrypt with salt
- **JWT Tokens**: Default access (30min) + Refresh (7 days), configurable via .env
- **Input Validation**: Pydantic schemas
- **Authorization**: Route-level user authentication
- **Ownership Validation**: Users can only access their own tasks
- **CORS Protection**: Configurable allowed origins

## API Endpoints

### Authentication

```
POST   /api/v1/auth/register    # User registration
POST   /api/v1/auth/login       # User login
POST   /api/v1/auth/refresh     # Refresh access token
```

### User Management

```
GET    /api/v1/users/me         # Get current user profile
PUT    /api/v1/users/me         # Update current user profile
```

### Task Management

```
POST   /api/v1/tasks/           # Create new task
GET    /api/v1/tasks/           # Get user tasks (with filters)
GET    /api/v1/tasks/{id}       # Get specific task
PUT    /api/v1/tasks/{id}       # Update task
DELETE /api/v1/tasks/{id}       # Delete task
```

### System

```
GET    /health                  # Health check endpoint
GET    /docs                    # API documentation (dev only)
```

## Data Flow Examples

### Task Creation Flow

```
1. Client Request
   POST /api/v1/tasks/
   Authorization: Bearer <token>
   Body: { title, description, priority, due_date }

2. Authentication Middleware
   ├── Extract and validate JWT token
   ├── Retrieve user from database
   └── Inject user into request context

3. Task Router
   ├── Validate request schema
   └── Forward to TaskService

4. Task Service
   ├── Apply business rules
   ├── Add owner_id to task data
   └── Call TaskRepository

5. Task Repository
   ├── Create SQLAlchemy Task model
   ├── Save to database
   └── Return created task

6. Response
   ├── Convert model to response schema
   └── Return JSON response to client
```

### User Authentication Flow

```
1. Login Request
   POST /api/v1/auth/login
   Body: { email, password }

2. AuthService
   ├── Validate user credentials
   ├── Check password hash
   └── Generate JWT tokens

3. Response
   {
     "access_token": "eyJ...",
     "refresh_token": "eyJ...",
     "token_type": "bearer"
   }

4. Subsequent Requests
   Authorization: Bearer <access_token>
```

## Technology Stack

### Backend Framework

- **FastAPI**: Modern Python web framework
- **Uvicorn**: ASGI server for production

### Database

- **PostgreSQL**: Primary database
- **SQLAlchemy**: ORM with async support
- **Asyncpg**: PostgreSQL async driver

### Authentication & Security

- **JWT**: Token-based authentication
- **bcrypt**: Password hashing
- **Pydantic**: Data validation and serialization

### Development & Testing

- **Pytest**: Testing framework
- **Pytest-asyncio**: Async testing support
- **HTTPX**: HTTP client for testing

## Performance Considerations

### Database Optimizations

- **Connection Pooling**: Configured for production environment
- **Async Operations**: Non-blocking database queries
- **Indexes**: On frequently queried fields (email, username, owner_id)
- **Query Optimization**: Repository pattern prevents N+1 queries

### API Performance

- **Dependency Injection**: Efficient resource management
- **Response Caching**: Stateless JWT tokens
- **Pagination**: Built-in limit/offset pagination
- **Input Validation**: Early request validation with Pydantic

### Scalability Considerations

- **Stateless Design**: JWT tokens enable horizontal scaling
- **Database Connection Pooling**: Handles multiple concurrent requests
- **Async Architecture**: Non-blocking I/O operations
- **Microservice Ready**: Clean architecture supports service decomposition

## Monitoring & Observability

### Health Checks

- **Database Connectivity**: Connection validation
- **Application Status**: Service health endpoints
- **Environment Information**: Configuration validation

### Logging

- **Request Tracing**: Request/response logging
- **Error Handling**: Comprehensive error logging

---

## Key Design Decisions

1. **Clean Architecture**: Separation of concerns with clear boundaries
2. **Repository Pattern**: Abstraction of data access logic
3. **Dependency Injection**: Loose coupling and testability
4. **Async/Await**: Non-blocking operations for better performance
5. **Type Safety**: Full Python type hints for better development experience
6. **JWT Authentication**: Stateless, scalable authentication mechanism
7. **Pydantic Validation**: Automatic input/output validation and documentation

This design provides a solid foundation for a scalable, maintainable, and secure task management API suitable for portfolio demonstration and real-world applications.
