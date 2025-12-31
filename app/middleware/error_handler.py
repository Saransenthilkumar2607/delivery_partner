"""
Global error handling middleware for the application.
This middleware catches all exceptions and returns a consistent JSON response.
"""
import json
import logging
import traceback
from django.http import JsonResponse
from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import DatabaseError as DjangoDatabaseError
from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework.exceptions import APIException as DRFAPIException

from app.helpers.exceptions import APIError


logger = logging.getLogger(__name__)


class ErrorHandlerMiddleware:
    """
    Global exception handling middleware that catches all exceptions
    and returns a JSON response with appropriate status codes.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_exception(self, request, exception):
        """
        Process the exception and return a JSON response.
        """
        # Only handle API requests (paths starting with /api/)
        if not request.path.startswith('/api/'):
            return None
            
        logger.error(
            f"Unhandled exception: {str(exception)}\n"
            f"Path: {request.path}\n"
            f"Method: {request.method}\n"
            f"Traceback: {traceback.format_exc()}",
            exc_info=True
        )
        
        # Handle Django REST Framework exceptions
        if isinstance(exception, DRFAPIException):
            response = drf_exception_handler(exception, {})
            if response is not None:
                return self._format_response(response, exception)
        
        # Handle our custom exceptions
        if isinstance(exception, APIError):
            return self._create_json_response(
                status_code=exception.status_code,
                message=exception.message,
                error_type=exception.__class__.__name__,
                details=exception.payload,
                errors=getattr(exception, 'errors', None)
            )
        
        # Handle Django's validation errors
        if isinstance(exception, DjangoValidationError):
            return self._create_json_response(
                status_code=400,
                message='Validation error',
                error_type='ValidationError',
                errors=exception.message_dict if hasattr(exception, 'message_dict') else str(exception)
            )
        
        # Handle database errors
        if isinstance(exception, DjangoDatabaseError):
            return self._create_json_response(
                status_code=500,
                message='A database error occurred',
                error_type='DatabaseError',
                details=str(exception) if settings.DEBUG else None
            )
        
        # Handle all other exceptions
        return self._create_json_response(
            status_code=500,
            message='An unexpected error occurred',
            error_type=exception.__class__.__name__,
            details=str(exception) if settings.DEBUG else None,
            traceback=traceback.format_exc() if settings.DEBUG else None
        )
    
    def _format_response(self, response, exception):
        """Format DRF response to our standard format."""
        if hasattr(exception, 'get_codes'):
            error_code = exception.get_codes()
        else:
            error_code = None
            
        response_data = {
            'status_code': response.status_code,
            'message': str(exception.detail) if hasattr(exception, 'detail') else str(exception),
            'error_type': exception.__class__.__name__,
        }
        
        if error_code:
            response_data['code'] = error_code
            
        if hasattr(exception, 'get_full_details'):
            response_data['errors'] = exception.get_full_details()
            
        response.data = response_data
        response.content = json.dumps(response_data)
        return response
    
    def _create_json_response(self, status_code, message, error_type, **kwargs):
        """Create a standardized JSON response."""
        response_data = {
            'status_code': status_code,
            'message': message,
            'error_type': error_type,
        }
        
        # Add additional fields if provided
        for key, value in kwargs.items():
            if value is not None:
                response_data[key] = value
                
        return JsonResponse(
            response_data,
            status=status_code,
            json_dumps_params={'indent': 2} if settings.DEBUG else None
        )
    
    def _add_cors_headers(self, response):
        """Add CORS headers to the response if needed."""
        if hasattr(settings, 'CORS_ALLOW_ALL_ORIGINS') and settings.CORS_ALLOW_ALL_ORIGINS:
            response['Access-Control-Allow-Origin'] = '*'
            response['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, DELETE, OPTIONS'
            response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
            response['Access-Control-Allow-Credentials'] = 'true'
