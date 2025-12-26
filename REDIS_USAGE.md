# Redis Integration Guide

This document explains how Redis is integrated into your Delivery Partner application.

## Setup

1. **Install Redis:**
   ```bash
   # On Ubuntu/Debian
   sudo apt-get install redis-server
   
   # On macOS (using Homebrew)
   brew install redis
   
   # On Windows (using WSL or Docker)
   docker run -d -p 6379:6379 redis:latest
   ```

2. **Install Python Redis packages:**
   ```bash
   pip install django-redis redis
   ```

3. **Configure environment variables:**
   Add to your `.env` file:
   ```
   REDIS_URL=redis://localhost:6379/0
   REDIS_CACHE_TIMEOUT=3600
   ```

## Redis Features Implemented

### 1. Caching
- **Query Result Caching**: Database query results are cached to improve performance
- **User Data Caching**: User information is cached after login for quick access
- **Automatic Cache Invalidation**: Cache is automatically cleared when data changes

### 2. Rate Limiting
- **Login Rate Limiting**: 5 login attempts per minute per IP address
- **API Rate Limiting**: Can be easily added to any endpoint

### 3. Session Management
- **Redis Sessions**: User sessions are stored in Redis for better scalability
- **Session Persistence**: Sessions survive server restarts

### 4. Health Monitoring
- **Redis Health Check**: Monitor Redis connection status
- **Cache Statistics**: View cache hit rates and memory usage

## Usage Examples

### Basic Caching
```python
from app.helpers.redis_service import RedisService

# Set a value
RedisService.set("my_key", "my_value", timeout=3600)

# Get a value
value = RedisService.get("my_key", "default_value")

# Delete a key
RedisService.delete("my_key")
```

### User Data Caching
```python
# Cache user data
user_data = {"id": 1, "name": "John", "email": "john@example.com"}
RedisService.cache_user_data(1, user_data, timeout=1800)

# Get cached user data
cached_user = RedisService.get_cached_user_data(1)

# Invalidate user cache
RedisService.invalidate_user_cache(1)
```

### Rate Limiting
```python
# Check rate limit (5 requests per minute)
if not RedisService.rate_limit_check("api_endpoint:user123", limit=5, window=60):
    return JsonResponse({"error": "Rate limit exceeded"}, status=429)
```

### Session Management
```python
# Store session
session_data = {"user_id": 1, "role": "ADMIN", "login_time": "2025-12-26T19:00:00Z"}
RedisService.set_session("session_abc123", session_data, timeout=3600)

# Get session
session = RedisService.get_session("session_abc123")

# Delete session
RedisService.delete_session("session_abc123")
```

### Query Result Caching
```python
# Cache query results
query_key = "users_list:page_1:size_10"
result = {"users": [...], "pagination": {...}}
RedisService.cache_query_result(query_key, result, timeout=300)

# Get cached query result
cached_result = RedisService.get_cached_query_result(query_key)

# Invalidate query cache
RedisService.invalidate_query_cache("users_list")
```

## API Endpoints

### Health Check
```bash
GET /api/health/
```
Returns system health status including Redis and database connectivity.

### Cache Statistics
```bash
GET /api/cache/stats/
```
Returns cache statistics including hit rates and memory usage.

### Clear Cache
```bash
POST /api/cache/clear/
```
Clears all cached data (admin only in production).

## Performance Benefits

1. **Reduced Database Load**: Frequently accessed data is cached in Redis
2. **Faster Response Times**: Cache hits are much faster than database queries
3. **Rate Limiting**: Prevents abuse and ensures fair usage
4. **Session Scalability**: Sessions can be shared across multiple server instances
5. **Real-time Monitoring**: Health checks and statistics for proactive management

## Best Practices

1. **Cache Keys**: Use descriptive, hierarchical keys (e.g., `user:123`, `query:users_list:page_1`)
2. **Timeouts**: Set appropriate timeouts to prevent stale data
3. **Cache Invalidation**: Always invalidate cache when data changes
4. **Error Handling**: Always handle Redis connection failures gracefully
5. **Memory Management**: Monitor Redis memory usage and set appropriate limits
6. **Security**: Secure Redis in production (password, network restrictions)

## Monitoring

Monitor your Redis instance using the health endpoints:

```bash
# Check system health
curl http://localhost:8000/api/health/

# Get cache statistics
curl http://localhost:8000/api/cache/stats/
```

## Troubleshooting

### Redis Connection Issues
1. Verify Redis is running: `redis-cli ping`
2. Check REDIS_URL in your environment variables
3. Ensure firewall allows connections to Redis port (6379)

### Cache Not Working
1. Check Redis connection: `RedisService.ping_redis()`
2. Verify cache keys: Use `redis-cli` to check if keys exist
3. Check cache timeouts: Keys may have expired

### Performance Issues
1. Monitor memory usage: `redis-cli info memory`
2. Check hit rates: Low hit rates indicate ineffective caching
3. Review cache key patterns: Ensure consistent key naming

## Security Considerations

1. **Redis Authentication**: Set a password in production
2. **Network Security**: Bind Redis to localhost or use VPN
3. **Data Encryption**: Encrypt sensitive data before caching
4. **Access Control**: Restrict cache clear endpoints to admin users
5. **Input Validation**: Validate all cache keys and values
