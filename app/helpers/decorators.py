from functools import wraps
from django.http import JsonResponse
import json
import logging

logger = logging.getLogger(__name__)

def handle_validation_error(view_func):
    """
    A decorator to handle validation errors in API views.
    Returns a JSON response with appropriate error message and status code.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        try:
            return view_func(request, *args, **kwargs)
        except json.JSONDecodeError:
            logger.error("Invalid JSON in request body")
            return JsonResponse(
                {"error": "Invalid JSON in request body"}, 
                status=400
            )
        except ValueError as e:
            logger.error(f"Validation error: {str(e)}")
            return JsonResponse(
                {"error": str(e)}, 
                status=400
            )
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            return JsonResponse(
                {"error": "An unexpected error occurred"}, 
                status=500
            )
    return wrapper

def require_authentication(view_func):
    """
    Decorator to ensure the request is authenticated.
    Checks for a valid authentication token in the request headers.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if not auth_header.startswith('Bearer '):
            return JsonResponse(
                {"error": "Authentication required"}, 
                status=401
            )
        # Here you would typically validate the token
        # For now, we'll just pass it through
        return view_func(request, *args, **kwargs)
    return wrapper

def validate_request(schema):
    """
    Decorator to validate request data against a schema.
    The schema should be a function that validates the request data.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            try:
                if request.method in ['POST', 'PUT', 'PATCH']:
                    if request.content_type == 'application/json':
                        try:
                            data = json.loads(request.body)
                        except json.JSONDecodeError:
                            return JsonResponse(
                                {"error": "Invalid JSON in request body"}, 
                                status=400
                            )
                        
                        # Validate data against schema
                        errors = schema.validate(data)
                        if errors:
                            return JsonResponse(
                                {"error": "Validation error", "details": errors}, 
                                status=400
                            )
                        
                        # Add validated data to request object
                        request.validated_data = data
                
                return view_func(request, *args, **kwargs)
            except Exception as e:
                logger.error(f"Request validation error: {str(e)}", exc_info=True)
                return JsonResponse(
                    {"error": "Request validation failed"}, 
                    status=400
                )
        return wrapper
    return decorator
