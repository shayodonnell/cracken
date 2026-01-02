"""Main FastAPI application for Cracken API."""

from fastapi import FastAPI

from app.api.v1 import auth, groups, tasks, completions
from app.config import settings

# Create FastAPI application instance
app = FastAPI(
    title=settings.PROJECT_NAME,
    debug=settings.DEBUG,
)

# Include API routers
app.include_router(
    auth.router,
    prefix=f"{settings.API_V1_PREFIX}/auth",
    tags=["Authentication"]
)

app.include_router(
    groups.router,
    prefix=f"{settings.API_V1_PREFIX}/groups",
    tags=["Groups"]
)

app.include_router(
    tasks.router,
    prefix=f"{settings.API_V1_PREFIX}/groups/{{group_id}}/tasks",
    tags=["Tasks"]
)

app.include_router(
    completions.router,
    prefix=f"{settings.API_V1_PREFIX}/groups/{{group_id}}/completions",
    tags=["completions"]

)


@app.get("/")
def root():
    """Root endpoint - API welcome message."""
    return {
        "message": "Welcome to Cracken API",
        "docs": "/docs",
        "version": "1.0.0"
    }


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
