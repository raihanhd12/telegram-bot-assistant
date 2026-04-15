"""
V1 Routes Module

This module contains all routes for API version 1.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/v1")

# Include domain routers


__all__ = ["router"]
