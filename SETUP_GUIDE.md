# Agentic-AI-Python Setup & Run Guide

## Prerequisites

- Python 3.11+
- PostgreSQL 14+
- MongoDB 6+
- Redis 7+

---

## Step 1: Clone and Setup Virtual Environment

```bash
cd Agentic-ai-python

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Linux/Mac:
source venv/bin/activate

# On Windows:
# venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

---

## Step 2: Setup Environment Variables

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```env
# Application
APP_NAME=Agentic-AI-Python
APP_ENV=development
DEBUG=True
SECRET_KEY=your-super-secret-key-change-in-production
API_HOST=0.0.0.0
API_PORT=8000
APP_URL=http://localhost:8000

# PostgreSQL Database
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/agentic_ai
DATABASE_SYNC_URL=postgresql://postgres:password@localhost:5432/agentic_ai

# MongoDB
MONGODB_URL=mongodb://localhost:27017
MONGODB_DATABASE=agentic_chat

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT Authentication
JWT_SECRET_KEY=your-jwt-secret-key
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Celery (Background Tasks)
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# Encryption (for secure chat)
ENCRYPTION_KEY=your-32-character-aes-key-here!!

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:5173

# OpenAI (Optional - for AI features)
OPENAI_API_KEY=sk-your-openai-key

# WhatsApp Integration (Optional)
WHATSAPP_VERIFY_TOKEN=your-verify-token
WHATSAPP_ACCESS_TOKEN=your-access-token

# Social Auth (Optional)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=
```

---

## Step 3: Setup Databases

### PostgreSQL

```bash
# Create database
psql -U postgres
CREATE DATABASE agentic_ai;
\q
```

### MongoDB

```bash
# MongoDB should auto-create the database on first use
# Just ensure MongoDB is running
mongod --dbpath /var/lib/mongodb
```

### Redis

```bash
# Start Redis server
redis-server
```

---

## Step 4: Run Database Migrations

```bash
# Make sure you're in the project directory with venv activated
cd Agentic-ai-python
source venv/bin/activate

# Run migrations
alembic upgrade head

# Verify migration
alembic current
```

---

## Step 5: Start the Application

### Option A: Development Mode (Single Process)

```bash
# Start the FastAPI server
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Option B: Production Mode (Multiple Workers)

```bash
# Start with Gunicorn + Uvicorn workers
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```

---

## Step 6: Start Celery Workers (For Background Tasks)

Open a new terminal:

```bash
cd Agentic-ai-python
source venv/bin/activate

# Start Celery worker
celery -A celery_app worker --loglevel=info

# Optional: Start Celery Beat for scheduled tasks
celery -A celery_app beat --loglevel=info
```

---

## Step 7: Verify Installation

### Check API Health

```bash
# Basic health check
curl http://localhost:8000/api/v1/health

# Deep health check (includes DB status)
curl http://localhost:8000/api/v1/health/deep
```

### Access API Documentation

Open in browser:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## Quick Start Script

Create a `start.sh` script for convenience:

```bash
#!/bin/bash

# Start all services
echo "Starting Agentic-AI-Python..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install/update dependencies
pip install -r requirements.txt --quiet

# Run migrations
echo "Running database migrations..."
alembic upgrade head

# Start the server
echo "Starting FastAPI server on http://localhost:8000"
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Make it executable:
```bash
chmod +x start.sh
./start.sh
```

---

## Docker Setup (Alternative)

If you prefer Docker:

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

---

## Common Commands

```bash
# Run server
uvicorn main:app --reload

# Run migrations
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "description"

# Rollback migration
alembic downgrade -1

# Start Celery worker
celery -A celery_app worker -l info

# Run tests
pytest

# Check code quality
flake8 app/
mypy app/
```

---

## Troubleshooting

### Database Connection Error
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Check MongoDB is running
sudo systemctl status mongod

# Check Redis is running
redis-cli ping
```

### Migration Errors
```bash
# Reset migrations (CAUTION: drops all data)
alembic downgrade base
alembic upgrade head
```

### Port Already in Use
```bash
# Find process using port 8000
lsof -i :8000

# Kill the process
kill -9 <PID>
```

---

## API Endpoints Overview

| Category | Base Path | Description |
|----------|-----------|-------------|
| Auth | `/api/v1/auth` | Login, Register, OAuth |
| Users | `/api/v1/user` | User management |
| Tenants | `/api/v1/tenant` | Multi-tenancy |
| Agents | `/api/v1/agents` | AI Agent CRUD |
| Knowledge Base | `/api/v1/knowledge-base` | KB management |
| Documents | `/api/v1/documents` | Document upload/processing |
| Assistants | `/api/v1/assistants` | Assistant connectors |
| Chat | `/api/v1/chat` | AI chat streaming |
| Sessions | `/api/v1/sessions` | Chat sessions |
| Health | `/api/v1/health` | Health checks |
| Metrics | `/api/v1/metrics` | System metrics |

---

## Next Steps

1. Create your first user via `/api/v1/auth/register`
2. Login to get JWT token via `/api/v1/auth/login`
3. Create a tenant and agent
4. Upload documents to knowledge base
5. Start chatting with your AI agent!
