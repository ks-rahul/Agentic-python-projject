# Agentic AI Python Backend

Unified Python backend for the Agentic AI Platform, replacing Laravel and Node.js backends.

## Features

- **FastAPI** - Modern, fast web framework
- **MySQL** - Primary database for structured data
- **MongoDB** - Chat sessions and messages storage
- **Redis** - Caching and Celery broker
- **Celery** - Background task processing
- **SQLAlchemy** - Async ORM for MySQL
- **Motor** - Async MongoDB driver
- **JWT Authentication** - Secure API authentication
- **RBAC** - Role-based access control

## Project Structure

```
Agentic-ai-python/
├── app/
│   ├── api/v1/routes/     # API route handlers
│   ├── core/              # Core utilities (config, security, logging)
│   ├── db/                # Database connections
│   ├── models/            # SQLAlchemy models
│   ├── schemas/           # Pydantic schemas
│   ├── services/          # Business logic
│   └── tasks/             # Celery tasks
├── alembic/               # Database migrations
├── main.py                # Application entry point
├── celery_app.py          # Celery configuration
├── requirements.txt       # Python dependencies
├── docker-compose.yml     # Docker services
└── Dockerfile             # Container build
```

## API Endpoints

### Authentication
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/register` - User registration
- `POST /api/v1/auth/logout` - User logout

### Agents
- `GET /api/v1/agents/list` - List agents
- `POST /api/v1/agents/create` - Create agent
- `GET /api/v1/agents/get/{id}` - Get agent
- `PUT /api/v1/agents/update/{id}` - Update agent
- `DELETE /api/v1/agents/delete/{id}` - Delete agent

### Knowledge Base
- `GET /api/v1/knowledge-base/list` - List knowledge bases
- `POST /api/v1/knowledge-base/create` - Create knowledge base
- `GET /api/v1/knowledge-base/get/{id}` - Get knowledge base

### Documents
- `GET /api/v1/documents/list` - List documents
- `POST /api/v1/documents/create` - Upload document
- `DELETE /api/v1/documents/delete/{id}` - Delete document

### Chat Sessions
- `POST /api/v1/sessions` - Create session
- `GET /api/v1/sessions` - List sessions
- `GET /api/v1/sessions/{id}` - Get session
- `GET /api/v1/sessions/{id}/chats` - Get session messages

### Chat
- `POST /api/v1/chat/tenants/{tenant_id}/agents/{agent_id}/stream` - Stream chat
- `WS /api/v1/chat/tenants/{tenant_id}/agents/{agent_id}/ws/{session_id}` - WebSocket chat

## Quick Start

### Using Docker

```bash
# Start all services
docker-compose up -d

# Run migrations
docker-compose exec api alembic upgrade head

# View logs
docker-compose logs -f api
```

### Local Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
.\venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env
# Edit .env with your settings

# Run migrations
alembic upgrade head

# Start the server
python main.py

# Start Celery worker (in another terminal)
celery -A celery_app worker --loglevel=info
```

## Environment Variables

See `.env.example` for all available configuration options.

## Database Migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1
```

## Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=app
```

## License

MIT
