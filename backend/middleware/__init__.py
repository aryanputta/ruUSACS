"""Middleware package for error handling and other cross-cutting concerns."""

from middleware.error_handler import register_error_handlers

__all__ = ["register_error_handlers"]
