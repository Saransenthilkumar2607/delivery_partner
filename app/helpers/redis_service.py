import json
import logging
from typing import Any, Optional, Union
from django.core.cache import cache
from app.helpers.redis_client import redis_client

logger = logging.getLogger(__name__)


class RedisService:
    """Service class for Redis operations including caching and session management"""
    
    @staticmethod
    def get(key: str, default: Any = None) -> Any:
        """
        Get value from Redis cache
        
        Args:
            key: Cache key
            default: Default value if key not found
            
        Returns:
            Cached value or default
        """
        try:
            value = cache.get(key)
            return value if value is not None else default
        except Exception as e:
            logger.error(f"Redis get error for key {key}: {str(e)}")
            return default
    
    @staticmethod
    def set(key: str, value: Any, timeout: Optional[int] = None) -> bool:
        """
        Set value in Redis cache
        
        Args:
            key: Cache key
            value: Value to cache
            timeout: Cache timeout in seconds (optional)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            return cache.set(key, value, timeout)
        except Exception as e:
            logger.error(f"Redis set error for key {key}: {str(e)}")
            return False
    
    @staticmethod
    def delete(key: str) -> bool:
        """
        Delete key from Redis cache
        
        Args:
            key: Cache key to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            return cache.delete(key)
        except Exception as e:
            logger.error(f"Redis delete error for key {key}: {str(e)}")
            return False
    
    @staticmethod
    def exists(key: str) -> bool:
        """
        Check if key exists in Redis
        
        Args:
            key: Cache key to check
            
        Returns:
            True if key exists, False otherwise
        """
        try:
            return cache.has_key(key)
        except Exception as e:
            logger.error(f"Redis exists error for key {key}: {str(e)}")
            return False
    
    @staticmethod
    def get_many(keys: list) -> dict:
        """
        Get multiple values from Redis cache
        
        Args:
            keys: List of cache keys
            
        Returns:
            Dictionary of key-value pairs
        """
        try:
            return cache.get_many(keys)
        except Exception as e:
            logger.error(f"Redis get_many error: {str(e)}")
            return {}
    
    @staticmethod
    def set_many(mapping: dict, timeout: Optional[int] = None) -> bool:
        """
        Set multiple values in Redis cache
        
        Args:
            mapping: Dictionary of key-value pairs
            timeout: Cache timeout in seconds (optional)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            cache.set_many(mapping, timeout)
            return True
        except Exception as e:
            logger.error(f"Redis set_many error: {str(e)}")
            return False
    
    @staticmethod
    def delete_many(keys: list) -> int:
        """
        Delete multiple keys from Redis cache
        
        Args:
            keys: List of cache keys to delete
            
        Returns:
            Number of keys deleted
        """
        try:
            return cache.delete_many(keys)
        except Exception as e:
            logger.error(f"Redis delete_many error: {str(e)}")
            return 0
    
    @staticmethod
    def clear() -> bool:
        """
        Clear all cache entries
        
        Returns:
            True if successful, False otherwise
        """
        try:
            return cache.clear()
        except Exception as e:
            logger.error(f"Redis clear error: {str(e)}")
            return False
    
    @staticmethod
    def increment(key: str, delta: int = 1) -> Optional[int]:
        """
        Increment a numeric value in Redis
        
        Args:
            key: Cache key
            delta: Increment amount (default: 1)
            
        Returns:
            New value or None if error
        """
        try:
            return cache.incr(key, delta)
        except Exception as e:
            logger.error(f"Redis increment error for key {key}: {str(e)}")
            return None
    
    @staticmethod
    def decrement(key: str, delta: int = 1) -> Optional[int]:
        """
        Decrement a numeric value in Redis
        
        Args:
            key: Cache key
            delta: Decrement amount (default: 1)
            
        Returns:
            New value or None if error
        """
        try:
            return cache.decr(key, delta)
        except Exception as e:
            logger.error(f"Redis decrement error for key {key}: {str(e)}")
            return None
    
    @staticmethod
    def set_session(session_id: str, session_data: dict, timeout: int = 3600) -> bool:
        """
        Store session data in Redis
        
        Args:
            session_id: Session identifier
            session_data: Session data to store
            timeout: Session timeout in seconds (default: 1 hour)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            session_key = f"session:{session_id}"
            return RedisService.set(session_key, json.dumps(session_data), timeout)
        except Exception as e:
            logger.error(f"Redis session set error: {str(e)}")
            return False
    
    @staticmethod
    def get_session(session_id: str) -> Optional[dict]:
        """
        Get session data from Redis
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session data or None if not found
        """
        try:
            session_key = f"session:{session_id}"
            session_data = RedisService.get(session_key)
            if session_data:
                return json.loads(session_data)
            return None
        except Exception as e:
            logger.error(f"Redis session get error: {str(e)}")
            return None
    
    @staticmethod
    def delete_session(session_id: str) -> bool:
        """
        Delete session from Redis
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if successful, False otherwise
        """
        try:
            session_key = f"session:{session_id}"
            return RedisService.delete(session_key)
        except Exception as e:
            logger.error(f"Redis session delete error: {str(e)}")
            return False
    
    @staticmethod
    def cache_user_data(user_id: int, user_data: dict, timeout: int = 1800) -> bool:
        """
        Cache user data for quick access
        
        Args:
            user_id: User ID
            user_data: User data to cache
            timeout: Cache timeout in seconds (default: 30 minutes)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            user_key = f"user:{user_id}"
            return RedisService.set(user_key, user_data, timeout)
        except Exception as e:
            logger.error(f"Redis user cache set error: {str(e)}")
            return False
    
    @staticmethod
    def get_cached_user_data(user_id: int) -> Optional[dict]:
        """
        Get cached user data
        
        Args:
            user_id: User ID
            
        Returns:
            Cached user data or None if not found
        """
        try:
            user_key = f"user:{user_id}"
            return RedisService.get(user_key)
        except Exception as e:
            logger.error(f"Redis user cache get error: {str(e)}")
            return None
    
    @staticmethod
    def invalidate_user_cache(user_id: int) -> bool:
        """
        Invalidate user cache
        
        Args:
            user_id: User ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            user_key = f"user:{user_id}"
            return RedisService.delete(user_key)
        except Exception as e:
            logger.error(f"Redis user cache delete error: {str(e)}")
            return False
    
    @staticmethod
    def cache_query_result(query_key: str, result_data: Any, timeout: int = 600) -> bool:
        """
        Cache database query results
        
        Args:
            query_key: Unique query identifier
            result_data: Query result to cache
            timeout: Cache timeout in seconds (default: 10 minutes)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            cache_key = f"query:{query_key}"
            return RedisService.set(cache_key, result_data, timeout)
        except Exception as e:
            logger.error(f"Redis query cache set error: {str(e)}")
            return False
    
    @staticmethod
    def get_cached_query_result(query_key: str) -> Any:
        """
        Get cached database query result
        
        Args:
            query_key: Unique query identifier
            
        Returns:
            Cached query result or None if not found
        """
        try:
            cache_key = f"query:{query_key}"
            return RedisService.get(cache_key)
        except Exception as e:
            logger.error(f"Redis query cache get error: {str(e)}")
            return None
    
    @staticmethod
    def invalidate_query_cache(query_pattern: str) -> int:
        """
        Invalidate query cache by pattern
        
        Args:
            query_pattern: Pattern to match query keys
            
        Returns:
            Number of keys deleted
        """
        try:
            # This requires direct redis_client for pattern matching
            pattern = f"query:{query_pattern}*"
            keys = redis_client.keys(pattern)
            if keys:
                return redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Redis query cache invalidate error: {str(e)}")
            return 0
    
    @staticmethod
    def rate_limit_check(identifier: str, limit: int, window: int) -> bool:
        """
        Check rate limit for API endpoints
        
        Args:
            identifier: Unique identifier (IP, user ID, etc.)
            limit: Number of allowed requests
            window: Time window in seconds
            
        Returns:
            True if within limit, False if exceeded
        """
        try:
            rate_limit_key = f"rate_limit:{identifier}"
            current_count = RedisService.get(rate_limit_key, 0)
            
            if current_count >= limit:
                return False
            
            # Increment counter
            RedisService.increment(rate_limit_key)
            
            # Set expiration if this is the first request in window
            if current_count == 0:
                RedisService.set(rate_limit_key, 1, window)
            
            return True
        except Exception as e:
            logger.error(f"Redis rate limit check error: {str(e)}")
            return True  # Allow request if Redis fails
    
    @staticmethod
    def get_redis_info() -> dict:
        """
        Get Redis server information
        
        Returns:
            Redis server info dictionary
        """
        try:
            return redis_client.info()
        except Exception as e:
            logger.error(f"Redis info error: {str(e)}")
            return {}
    
    @staticmethod
    def ping_redis() -> bool:
        """
        Test Redis connection
        
        Returns:
            True if Redis is responsive, False otherwise
        """
        try:
            return redis_client.ping()
        except Exception as e:
            logger.error(f"Redis ping error: {str(e)}")
            return False
