"""
This file makes the middleware directory a Python package.
"""
from .error_handler import ErrorHandlerMiddleware

__all__ = ['ErrorHandlerMiddleware']
