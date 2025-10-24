"""Root controller for basic application endpoints."""

import os
from fastapi import APIRouter
from loguru import logger


router = APIRouter(tags=["root"])


@router.get("/")
async def root():
    """Root endpoint with basic API information."""
    logger.info("Root endpoint accessed")
    return {
        "message": "Welcome to Contramate API",
        "version": "0.1.0",
        "status": "running"
    }


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    logger.info("Health check endpoint accessed")
    return {
        "status": "healthy",
        "environment": os.getenv("RUNTIME_ENV", "unknown"),
        "host_system": os.getenv("HOST_SYSTEM", "unknown")
    }
