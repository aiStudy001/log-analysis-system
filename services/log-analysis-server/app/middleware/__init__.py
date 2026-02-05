"""
Middleware package

Contains custom middleware for the application.
"""
from .error_handler import error_handler_middleware

__all__ = ["error_handler_middleware"]
