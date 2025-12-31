from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import HttpRequest
from typing import Any, Dict, Optional, Type
from rest_framework.serializers import Serializer
import logging

logger = logging.getLogger(__name__)

class PaginationHelper:
    """Helper class for handling pagination with type hints and better error handling"""
    
    @classmethod
    def paginate_queryset(
        cls, 
        queryset, 
        request: HttpRequest, 
        serializer_class: Optional[Type[Serializer]] = None, 
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Paginate a queryset with optional serialization
        
        Args:
            queryset: Django queryset to paginate
            request: HTTP request object
            serializer_class: Optional serializer class
            context: Optional context for serializer
            
        Returns:
            dict: Contains paginated data and pagination info
        """
        try:
            page, page_size, paginate = cls.get_pagination_params(request)
            
            if not paginate:
                data = {
                    'data': cls._serialize_queryset(queryset, serializer_class, context or {}),
                    'pagination': None
                }
                return data
            
            paginator = Paginator(queryset, page_size)
            
            try:
                page_obj = paginator.page(page)
            except PageNotAnInteger:
                page_obj = paginator.page(1)
                page = 1
            except EmptyPage:
                page_obj = paginator.page(paginator.num_pages)
                page = paginator.num_pages
                
            data = {
                'data': cls._serialize_queryset(page_obj.object_list, serializer_class, context or {}),
                'pagination': {
                    'current_page': page,
                    'total_pages': paginator.num_pages,
                    'total_items': paginator.count,
                    'page_size': page_size,
                    'has_next': page_obj.has_next(),
                    'has_previous': page_obj.has_previous(),
                }
            }
            
            return data
            
        except Exception as e:
            logger.error(f"Error in paginate_queryset: {str(e)}", exc_info=True)
            from app.helpers.exceptions import APIError
            raise APIError("Failed to paginate results") from e
    
    @staticmethod
    def _serialize_queryset(queryset, serializer_class=None, context=None):
        """Helper method to handle serialization"""
        if serializer_class:
            return serializer_class(queryset, many=True, context=context).data
        return list(queryset)
    
    @staticmethod
    def get_pagination_params(request: HttpRequest) -> tuple[int, int, bool]:
        """
        Extract pagination parameters from request
        
        Args:
            request: Django request object
            
        Returns:
            tuple: (page, page_size, paginate)
        """
        try:
            page = max(1, int(request.GET.get('page', 1)))
            page_size = min(max(1, int(request.GET.get('page_size', 10))), 100)
            paginate = request.GET.get('paginate', 'true').lower() == 'true'
            return page, page_size, paginate
        except (ValueError, TypeError) as e:
            logger.warning(f"Invalid pagination params: {e}, using defaults")
            return 1, 10, True
