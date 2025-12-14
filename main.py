"""
Agentic AI Python Backend
Main application entry point
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.logging import setup_logging, get_logger
from app.db.postgresql import init_db
from app.db.mongodb import connect_mongodb, close_mongodb
from app.db.redis import connect_redis, close_redis
from app.api.v1.router import api_router

# Setup logging
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("Starting Agentic AI Python Backend...")
    
    try:
        # Initialize databases
        await init_db()
        logger.info("PostgreSQL initialized")
        
        await connect_mongodb()
        logger.info("MongoDB connected")
        
        await connect_redis()
        logger.info("Redis connected")
        
    except Exception as e:
        logger.error(f"Startup error: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    await close_mongodb()
    await close_redis()


# Create FastAPI application
app = FastAPI(
    title="Agentic AI Python Backend",
    description="Unified Python backend for Agentic AI Platform",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
origins = settings.cors_origins_list
# In development, allow all origins if "*" is in the list
if settings.DEBUG and "*" in origins:
    origins = ["*"]
    
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True if "*" not in origins else False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
)


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc: Exception):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "An unexpected error occurred",
            "detail": str(exc) if settings.DEBUG else "Internal Server Error"
        }
    )


# Include API router
app.include_router(api_router, prefix="/api/v1")


# Root endpoint
@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint."""
    return {
        "message": "Welcome to Agentic AI Python Backend",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Agentic AI Python Backend",
        "version": "1.0.0"
    }


# Public endpoints (no auth required)
@app.get("/api/v1/get-agent-configuration/{agent_id}")
async def get_agent_configuration_public(agent_id: str):
    """Get agent configuration (public endpoint for chat widget)."""
    from app.db.postgresql import AsyncSessionLocal
    from app.services.agent_service import AgentService
    
    async with AsyncSessionLocal() as db:
        agent_service = AgentService(db)
        config = await agent_service.get_full_configuration(agent_id)
        
        if not config:
            return JSONResponse(
                status_code=404,
                content={"error": "Agent not found"}
            )
        
        return config


@app.get("/api/v1/get-assistant-configurations")
async def get_assistant_configurations_public():
    """Get assistant configurations (public endpoint)."""
    # TODO: Implement
    return {"configurations": []}


@app.get("/api/v1/get-assistant-intent-configurations/{agent_id}")
async def get_assistant_intent_configurations_public(agent_id: str):
    """Get assistant intent configurations (public endpoint)."""
    from app.db.postgresql import AsyncSessionLocal
    from app.services.assistant_service import AssistantService
    
    async with AsyncSessionLocal() as db:
        assistant_service = AssistantService(db)
        configs = await assistant_service.get_intent_configurations_by_agent(agent_id)
        return {"configurations": configs}


if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"Starting server on {settings.API_HOST}:{settings.API_PORT}")
    
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG
    )
