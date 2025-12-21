from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.database import init_db
from app.routers import (
    upload_router,
    cleaning_router,
    insights_router,
    charts_router,
    ml_router,
    export_router,
    preview_router,
    auth_router
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler - runs on startup and shutdown."""
    # Startup: Initialize database
    init_db()
    yield
    # Shutdown: cleanup if needed
    pass


# Create FastAPI app
app = FastAPI(
    title="Adaptiva Data Analysis API",
    description="A comprehensive FastAPI backend for data analysis with file upload, data cleaning, insights generation, chart creation, ML models, and export capabilities",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router, prefix="/api")
app.include_router(upload_router, prefix="/api")
app.include_router(cleaning_router, prefix="/api")
app.include_router(insights_router, prefix="/api")
app.include_router(charts_router, prefix="/api")
app.include_router(ml_router, prefix="/api")
app.include_router(export_router, prefix="/api")
app.include_router(preview_router, prefix="/api")


@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint with API information
    """
    return {
        "message": "Welcome to Adaptiva Data Analysis API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc",
        "endpoints": {
            "auth": "/api/auth",
            "upload": "/api/upload",
            "cleaning": "/api/cleaning",
            "cleaning_enhanced": "/api/cleaning/enhanced",
            "insights": "/api/insights/{file_id}",
            "charts": "/api/charts",
            "ml": "/api/ml/train",
            "export": "/api/export",
            "preview": "/api/preview"
        }
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint
    """
    return {"status": "healthy"}


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler for unhandled exceptions
    """
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc)
        }
    )


if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
