from django.urls import path
from app.api.health.controller import HealthCheckController, CacheStatsController, CacheClearController

# Health check routes
urlpatterns = [
    path('health/', HealthCheckController.as_view(), name='health_check'),
    path('cache/stats/', CacheStatsController.as_view(), name='cache_stats'),
    path('cache/clear/', CacheClearController.as_view(), name='cache_clear'),
]
