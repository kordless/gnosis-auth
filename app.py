"""
Gnosis Auth Server Application - FastAPI Version
"""
import os
import sys
from contextlib import asynccontextmanager
import fastapi
from fastapi import FastAPI, Request
from fastapi.exceptions import StarletteHTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse, RedirectResponse
import uvicorn

# Import configuration and logging
from core.config import config, logger, STORAGE_PATH, SECRET_KEY, APP_NAME, APP_DOMAIN

# Import routers
from web.routes import (
    auth_router, user_router, session_router, oauth_router, 
    health_router, pages_router, jwt_router, api_router
)

# Environment detection
IS_DEVELOPMENT = config.is_development
ENABLE_DEV_ENDPOINTS = config.enable_dev_endpoints

from core.models.base import get_ndb_client

# ... (other imports)

# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info(f"Gnosis Auth Server starting...")
    # Initialize the NDB client singleton on application startup
    get_ndb_client()
    yield
    # Shutdown
    logger.info("Gnosis Auth Server shutting down...")

# Create FastAPI app
app = FastAPI(
    title=APP_NAME,
    description="Authentication and authorization service for Gnosis ecosystem",
    version="1.0.0",
    docs_url="/docs" if IS_DEVELOPMENT else None,
    redoc_url="/redoc" if IS_DEVELOPMENT else None,
    lifespan=lifespan
)

# Add Session Middleware
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

# Configure CORS
cors_origins = os.environ.get("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add NDB Context Middleware
@app.middleware("http")
async def ndb_context_middleware(request: Request, call_next):
    """Wrap all requests in NDB context"""
    client = get_ndb_client()
    with client.context():
        response = await call_next(request)
    return response

# Mount static files
app.mount("/static", StaticFiles(directory="web/static"), name="static")

# Include routers
app.include_router(health_router, tags=["health"])
app.include_router(auth_router, prefix="/api/auth", tags=["authentication"])
app.include_router(user_router, prefix="/api/users", tags=["users"])
app.include_router(session_router, prefix="/api/sessions", tags=["sessions"])
app.include_router(oauth_router, prefix="/api/oauth", tags=["oauth"])
app.include_router(jwt_router, tags=["jwt"])
app.include_router(api_router, prefix="/api", tags=["api"])
app.include_router(pages_router, include_in_schema=False)

# Include dev endpoints if enabled
if IS_DEVELOPMENT and ENABLE_DEV_ENDPOINTS:
    try:
        from web.routes.dev import dev_router
        app.include_router(dev_router, prefix="/dev", tags=["development"])
        logger.info("Development endpoints enabled at /dev/*")
    except ImportError:
        logger.warning("Development routes not available")

# Catch-all route MUST BE LAST
@app.api_route("/{path_name:path}", include_in_schema=False)
async def catch_all(request: Request, path_name: str):
    """Redirects any unhandled path to the /search discovery endpoint."""
    original_path = request.url.path
    original_method = request.method
    redirect_url = f"/search?original_path={original_path}&original_method={original_method}"
    return RedirectResponse(url=redirect_url, status_code=307)