"""
FastAPI Application Entry Point for AI Markdown Workspace.
Configures middleware, routes, Jinja2 filters, and static files.
"""
import os
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, HTMLResponse

from app.config import settings
from app.database import init_db
from app.services.timezone_service import (
    jinja_wib_filter,
    jinja_from_iso_filter,
    jinja_wib_relative_filter,
)
from app.services.markdown_engine import render_markdown


# Define paths
BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler - initialize DB on startup."""
    # Startup: Initialize database
    await init_db()
    print(f"🚀 {settings.APP_NAME} started")
    yield
    # Shutdown: cleanup if needed
    print(f"👋 {settings.APP_NAME} shutting down")


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="AI-powered Markdown workspace with HTMX",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Configure Jinja2 templates
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Register custom Jinja2 filters
templates.env.filters["wib"] = jinja_wib_filter
templates.env.filters["from_iso"] = jinja_from_iso_filter
templates.env.filters["wib_relative"] = jinja_wib_relative_filter
templates.env.filters["render_markdown"] = render_markdown


# Import routers
from app.routers import (
    chat,
    files,
    sqlite_viewer,
    settings as settings_router,
    builders,
    rag,
    workspaces,
    audit,
    export,
)

# Initialize templates for routers that need direct access
chat.set_templates(templates)

# Include routers
app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(files.router, prefix="/files", tags=["files"])
app.include_router(sqlite_viewer.router, prefix="/sqlite", tags=["sqlite"])
app.include_router(settings_router.router, prefix="/settings", tags=["settings"])
app.include_router(builders.router, prefix="/builders", tags=["builders"])
app.include_router(rag.router, prefix="/rag", tags=["rag"])
app.include_router(workspaces.router, prefix="/workspaces", tags=["workspaces"])
app.include_router(audit.router, prefix="/audit", tags=["audit"])
app.include_router(export.router, prefix="/export", tags=["export"])


@app.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint - redirect to chat."""
    return RedirectResponse(url="/chat")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "app": settings.APP_NAME}


@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    """Handle 404 errors with custom page."""
    return templates.TemplateResponse(
        "pages/error.html",
        {"request": request, "error_code": 404, "error_message": "Page not found"},
        status_code=404,
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: HTTPException):
    """Handle 500 errors with custom page."""
    return templates.TemplateResponse(
        "pages/error.html",
        {"request": request, "error_code": 500, "error_message": "Internal server error"},
        status_code=500,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
    )
