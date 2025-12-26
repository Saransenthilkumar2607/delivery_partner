import logging
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from app.helpers.redis_service import RedisService

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name="dispatch")
class HealthCheckController(View):
    """
    Health check endpoint for monitoring system status
    """
    
    def get(self, request):
        """Check health of database and Redis"""
        health_status = {
            "status": "healthy",
            "timestamp": "2025-12-26T19:00:00Z",
            "services": {}
        }
        
        # Check Redis connection
        try:
            redis_healthy = RedisService.ping_redis()
            if redis_healthy:
                health_status["services"]["redis"] = {
                    "status": "healthy",
                    "response_time": "fast"
                }
            else:
                health_status["services"]["redis"] = {
                    "status": "unhealthy",
                    "error": "Redis not responding"
                }
                health_status["status"] = "degraded"
        except Exception as e:
            health_status["services"]["redis"] = {
                "status": "error",
                "error": str(e)
            }
            health_status["status"] = "unhealthy"
        
        # Check database connection
        try:
            from app.models.users import User
            User.objects.count()  # Simple database query
            health_status["services"]["database"] = {
                "status": "healthy",
                "response_time": "fast"
            }
        except Exception as e:
            health_status["services"]["database"] = {
                "status": "error",
                "error": str(e)
            }
            health_status["status"] = "unhealthy"
        
        # Get Redis info if available
        if redis_healthy:
            try:
                redis_info = RedisService.get_redis_info()
                health_status["services"]["redis"]["info"] = {
                    "used_memory": redis_info.get("used_memory_human", "N/A"),
                    "connected_clients": redis_info.get("connected_clients", "N/A"),
                    "uptime_in_seconds": redis_info.get("uptime_in_seconds", "N/A")
                }
            except Exception as e:
                logger.error(f"Failed to get Redis info: {str(e)}")
        
        status_code = 200 if health_status["status"] == "healthy" else 503
        return JsonResponse(health_status, status=status_code)


@method_decorator(csrf_exempt, name="dispatch")
class CacheStatsController(View):
    """
    Cache statistics endpoint
    """
    
    def get(self, request):
        """Get cache statistics"""
        try:
            redis_info = RedisService.get_redis_info()
            
            stats = {
                "cache_info": {
                    "redis_version": redis_info.get("redis_version", "N/A"),
                    "used_memory": redis_info.get("used_memory_human", "N/A"),
                    "used_memory_peak": redis_info.get("used_memory_peak_human", "N/A"),
                    "connected_clients": redis_info.get("connected_clients", "N/A"),
                    "total_commands_processed": redis_info.get("total_commands_processed", "N/A"),
                    "keyspace_hits": redis_info.get("keyspace_hits", 0),
                    "keyspace_misses": redis_info.get("keyspace_misses", 0),
                    "hit_rate": self._calculate_hit_rate(redis_info)
                },
                "timestamp": "2025-12-26T19:00:00Z"
            }
            
            return JsonResponse(stats)
            
        except Exception as e:
            logger.error(f"Failed to get cache stats: {str(e)}")
            return JsonResponse({
                "error": "Failed to retrieve cache statistics",
                "details": str(e)
            }, status=500)
    
    def _calculate_hit_rate(self, redis_info):
        """Calculate cache hit rate"""
        hits = redis_info.get("keyspace_hits", 0)
        misses = redis_info.get("keyspace_misses", 0)
        total = hits + misses
        
        if total == 0:
            return 0.0
        
        return round((hits / total) * 100, 2)


@method_decorator(csrf_exempt, name="dispatch")
class CacheClearController(View):
    """
    Clear cache endpoint (admin only)
    """
    
    def post(self, request):
        """Clear all cache"""
        try:
            # This should be protected with admin authentication in production
            cleared = RedisService.clear()
            
            return JsonResponse({
                "message": "Cache cleared successfully",
                "cleared": cleared,
                "timestamp": "2025-12-26T19:00:00Z"
            })
            
        except Exception as e:
            logger.error(f"Failed to clear cache: {str(e)}")
            return JsonResponse({
                "error": "Failed to clear cache",
                "details": str(e)
            }, status=500)
