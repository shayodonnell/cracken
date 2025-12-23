# Cracken - Chore Rotation App

A FastAPI-based backend for managing household chores and task rotation among housemates.

## Features

- User authentication with JWT tokens
- Group management with invite codes
- Task tracking with rotation logic (whose turn is it?)
- Completion history to see who's pulling their weight
- PostgreSQL database with Alembic migrations

## Tech Stack

- **FastAPI** - Modern Python web framework
- **SQLAlchemy 2.0** - ORM for database operations
- **PostgreSQL** - Database (running in Docker)
- **Alembic** - Database migrations
- **JWT** - Token-based authentication
- **Bcrypt** - Password hashing

## Setup

### Prerequisites

- Python 3.13+
- Docker Desktop (for PostgreSQL)

### Installation

1. **Clone the repository**
   ```bash
   cd /Users/shay/Desktop/cracken
   ```

2. **Create and activate virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   pip install email-validator  # Required for Pydantic EmailStr
   ```

4. **Start PostgreSQL with Docker**
   ```bash
   docker-compose up -d
   ```

5. **Run database migrations**
   ```bash
   alembic upgrade head
   ```

6. **Start the development server**
   ```bash
   uvicorn app.main:app --reload
   ```

The API will be available at `http://localhost:8000`

## API Documentation

Once the server is running, visit:
- **Interactive API docs (Swagger UI)**: http://localhost:8000/docs
- **Alternative docs (ReDoc)**: http://localhost:8000/redoc

## Quick Start

### 1. Register a new user

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "name": "Your Name",
    "password": "yourpassword"
  }'
```

### 2. Login to get access token

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=user@example.com&password=yourpassword"
```

### 3. Use the token to access protected endpoints

```bash
curl -X GET http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

## Database Management

### Create a new migration
```bash
alembic revision --autogenerate -m "Description of changes"
```

### Apply migrations
```bash
alembic upgrade head
```

### Rollback one migration
```bash
alembic downgrade -1
```

### View migration history
```bash
alembic history
```

## Project Structure

```
cracken/
├── app/
│   ├── api/
│   │   ├── deps.py          # FastAPI dependencies (auth, db)
│   │   └── v1/
│   │       └── auth.py      # Authentication endpoints
│   ├── core/
│   │   └── security.py      # Password hashing, JWT tokens
│   ├── models/              # SQLAlchemy models
│   │   ├── user.py
│   │   ├── group.py
│   │   ├── task.py
│   │   └── completion.py
│   ├── schemas/             # Pydantic schemas
│   │   ├── user.py
│   │   ├── group.py
│   │   ├── task.py
│   │   └── completion.py
│   ├── utils/
│   │   └── invite_code.py   # Invite code generation
│   ├── config.py            # Settings management
│   ├── database.py          # Database connection
│   └── main.py              # FastAPI application
├── alembic/                 # Database migrations
├── docker-compose.yml       # PostgreSQL container
├── requirements.txt         # Python dependencies
└── .env                     # Environment variables
```

## Environment Variables

Copy `.env.example` to `.env` and update values:

```env
DATABASE_URL=postgresql+psycopg://cracken_user:cracken_password@localhost:5432/cracken_db
SECRET_KEY=your-secret-key-here  # Generate with: openssl rand -hex 32
ACCESS_TOKEN_EXPIRE_MINUTES=30
PROJECT_NAME=Cracken API
DEBUG=True
```

## Development

The server runs with auto-reload enabled, so code changes will automatically restart the server.

### Stop the database
```bash
docker-compose down
```

### Reset the database (WARNING: deletes all data)
```bash
docker-compose down -v
docker-compose up -d
alembic upgrade head
```

## Next Steps

The authentication system is complete! Next features to implement:
- Group management endpoints (create, join, leave)
- Task management endpoints (create, update, list)
- Completion tracking (mark tasks as done)
- Rotation logic (whose turn is it?)
- User profile management

## License

MIT
