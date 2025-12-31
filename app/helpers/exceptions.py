"""
Custom exceptions for the application.
These exceptions are used to handle various error scenarios in a consistent way.
"""
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import DatabaseError as DjangoDatabaseError


class APIError(Exception):
    """Base class for all API exceptions"""
    status_code = 500
    message = 'An unexpected error occurred'
    
    def __init__(self, message=None, status_code=None, payload=None):
        super().__init__()
        if message is not None:
            self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload
    
    def to_dict(self):
        rv = dict(self.payload or {})
        rv['message'] = self.message
        rv['status_code'] = self.status_code
        return rv


class BadRequestError(APIError):
    """Raised when the request is malformed or missing required parameters"""
    status_code = 400
    message = 'Bad request'


class UnauthorizedError(APIError):
    """Raised when authentication is required but not provided or invalid"""
    status_code = 401
    message = 'Authentication required'


class ForbiddenError(APIError):
    """Raised when the user doesn't have permission to access the resource"""
    status_code = 403
    message = 'Permission denied'


class NotFoundError(APIError):
    """Raised when a requested resource is not found"""
    status_code = 404
    message = 'Resource not found'


class MethodNotAllowedError(APIError):
    """Raised when the HTTP method is not allowed for the requested resource"""
    status_code = 405
    message = 'Method not allowed'


class ConflictError(APIError):
    """Raised when there's a conflict with the current state of the resource"""
    status_code = 409
    message = 'Conflict with the current state of the resource'


class ValidationError(APIError, DjangoValidationError):
    """Raised when validation fails"""
    status_code = 422
    message = 'Validation failed'
    
    def __init__(self, errors=None, **kwargs):
        super().__init__(**kwargs)
        self.errors = errors or {}
    
    def to_dict(self):
        rv = super().to_dict()
        if self.errors:
            rv['errors'] = self.errors
        return rv


class RateLimitExceededError(APIError):
    """Raised when the rate limit has been exceeded"""
    status_code = 429
    message = 'Rate limit exceeded'


class InternalServerError(APIError):
    """Raised when an unexpected error occurs on the server"""
    status_code = 500
    message = 'Internal server error'


class ServiceUnavailableError(APIError):
    """Raised when the server is temporarily unable to handle the request"""
    status_code = 503
    message = 'Service temporarily unavailable'


# Alias to avoid naming conflict with Django's DatabaseError
DBError = DatabaseError = APIError