# Task Management API

A production-ready FastAPI application for team task management with PostgreSQL backend, featuring comprehensive authentication, role-based access, and real-time collaboration capabilities.

## 🚀 Features

- **User Management**: Authentication, email verification, and profile management
- **Team Collaboration**: Multi-tenant architecture with team-based access control
- **Project Organization**: Hierarchical project and task management
- **Task Dependencies**: Complex workflow management with blocking relationships
- **Assignment Tracking**: Multi-user task assignments with audit trails
- **Rich Metadata**: Priorities, due dates, time tracking, and status workflows
- **Soft Deletes**: Data retention and audit compliance
- **Type Safety**: Full mypy compatibility with strict type checking

## 🏗️ Architecture

Built with modern Python best practices and production-ready patterns:

- **FastAPI**: High-performance async web framework
- **SQLAlchemy 2.0**: Modern async ORM with declarative models
- **PostgreSQL**: Robust relational database with UUID primary keys
- **Alembic**: Database migration management
- **Pydantic**: Data validation and settings management
- **JWT Authentication**: Secure token-based authentication
- **Connection Pooling**: Optimized database performance

## 📋 Prerequisites

- Python 3.13+
- PostgreSQL 17+
- Git

## ⚡ Quick Start

### 1. Clone and Setup

```bash
git clone https://github.com/username/task-management-api.git
cd task-management-api
```

### 2. Install Dependencies

```bash
pip install -r requirements-dev.txt
pre-commit install
```

### 3. Database Setup

```bash
# Create PostgreSQL database
createdb task_management

# Configure environment
cp .env.example .env
# Edit .env with your database credentials

# Run migrations
alembic upgrade head
```

### 4. Run Application

```bash
# Development server
python src/main.py

# Or with uvicorn directly
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

## 🔧 Development

### Code Quality

```bash
# Linting and formatting
ruff check .
ruff format .

# Type checking
mypy src

# Run all pre-commit hooks
pre-commit run --all-files
```

### Testing

```bash
# Run all tests with coverage
pytest

# Specific test suites
pytest tests/models/     # Model tests
pytest tests/core/       # Core functionality
pytest -v               # Verbose output
pytest --cov-report=html # HTML coverage report
```

### Database Management

```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Check current revision
alembic current

# Show migration history
alembic history --verbose

# Downgrade one step
alembic downgrade -1
```

## 📊 Database Schema

### Core Models

- **Users**: Authentication, profiles, preferences
- **Teams**: Multi-tenant organization units
- **Projects**: Task containers within teams
- **Tasks**: Core work items with rich metadata
- **Assignments**: User-task relationships
- **Dependencies**: Task workflow management

### Key Features

- UUID primary keys for security
- Automatic timestamps with timezone support
- Soft delete functionality
- Optimized indexes for performance
- Foreign key constraints for data integrity

## 🛡️ Security Features

- JWT access and refresh tokens
- Bcrypt password hashing
- Email verification requirement
- Multi-tenant data isolation
- SQL injection prevention
- CORS configuration

## 🚀 Production Deployment

### Docker (Recommended)

```bash
# Build and run
docker-compose -f dockerfiles/docker-compose.dev.yml up --build

# Production build
docker build -f dockerfiles/Dockerfile.dev -t task-api .
```

### Manual Deployment

```bash
# Install production dependencies
pip install -r requirements.txt

# Run with Gunicorn
gunicorn src.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

## 📝 Environment Variables

Create `.env` file with:

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/task_management

# Application
DEBUG=false
SECRET_KEY=your-secret-key-here
ALLOWED_ORIGINS=https://yourdomain.com

# Email (optional)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

## 📈 Performance

- **Async/Await**: Non-blocking I/O operations
- **Connection Pooling**: Optimized database connections
- **Query Optimization**: Strategic indexing and foreign keys
- **In-Memory Testing**: Fast test suite with SQLite
- **Type Safety**: Compile-time error prevention

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Code Standards

- Follow PEP 8 style guidelines
- Use type hints throughout
- Write comprehensive tests
- Document complex business logic
- Run pre-commit hooks before committing

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- FastAPI team for the excellent framework
- SQLAlchemy team for the powerful ORM
- PostgreSQL community for the robust database

---

**Built with ❤️ using modern Python practices**
