from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger


class PaginationHelper:
    """Helper class for handling pagination"""
    
    @staticmethod
    def paginate_queryset(queryset, page, page_size=10):
        """
        Paginate a queryset and return pagination data
        
        Args:
            queryset: Django queryset to paginate
            page: Current page number (from request.GET)
            page_size: Number of items per page (default: 10)
            
        Returns:
            dict: Contains paginated data and pagination info
        """
        try:
            page_size = int(page_size)
        except (ValueError, TypeError):
            page_size = 10
            
        # Limit page size to prevent excessive queries
        page_size = min(page_size, 100)
        
        try:
            page = int(page)
        except (ValueError, TypeError):
            page = 1
            
        paginator = Paginator(queryset, page_size)
        
        try:
            page_obj = paginator.page(page)
        except PageNotAnInteger:
            # If page is not an integer, deliver first page
            page_obj = paginator.page(1)
            page = 1
        except EmptyPage:
            # If page is out of range, deliver last page
            page_obj = paginator.page(paginator.num_pages)
            page = paginator.num_pages
            
        return {
            'data': list(page_obj.object_list),
            'pagination': {
                'current_page': page,
                'total_pages': paginator.num_pages,
                'total_items': paginator.count,
                'page_size': page_size,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
            }
        }
    
    @staticmethod
    def get_pagination_params(request):
        """
        Extract pagination parameters from request
        
        Args:
            request: Django request object
            
        Returns:
            tuple: (page, page_size)
        """
        page = request.GET.get('page', 1)
        page_size = request.GET.get('page_size', 10)
        return page, page_size
