"""
Redis cache service for caching Firebase metadata
"""
import redis
import json
import logging
import os
from datetime import datetime
from functools import wraps
from typing import Any, Optional, Callable

logger = logging.getLogger(__name__)

class CacheService:
    """Redis-based cache service for Firebase data"""

    def __init__(self, host=None, port=None, db=None):
        """Initialize Redis connection with environment variable support"""
        # Use environment variables with fallbacks
        host = host or os.getenv('REDIS_HOST', '127.0.0.1')
        port = port or int(os.getenv('REDIS_PORT', '6379'))
        db = db or int(os.getenv('REDIS_DB', '0'))
        self.redis_client = None
        self.host = host
        self.port = port
        self.db = db
        self.enabled = False

        try:
            self.redis_client = redis.Redis(
                host=host,
                port=port,
                db=db,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2
            )
            # Test connection
            self.redis_client.ping()
            self.enabled = True
            logger.info(f"Redis cache connected successfully on {host}:{port}")
        except Exception as e:
            logger.warning(f"Redis cache unavailable: {str(e)}. Running without cache.")
            self.enabled = False

    def _serialize(self, data: Any) -> str:
        """Serialize data to JSON string, handling datetime objects"""
        def datetime_handler(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

        return json.dumps(data, default=datetime_handler)

    def _deserialize(self, data: str) -> Any:
        """Deserialize JSON string to Python object"""
        if data is None:
            return None
        return json.loads(data)

    def get(self, key: str) -> Optional[Any]:
        """Get cached value by key"""
        if not self.enabled:
            return None

        try:
            data = self.redis_client.get(key)
            if data:
                logger.debug(f"Cache HIT: {key}")
                return self._deserialize(data)
            logger.debug(f"Cache MISS: {key}")
            return None
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {str(e)}")
            return None

    def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """
        Set cached value with TTL (time to live in seconds)
        Default TTL: 300 seconds (5 minutes)
        """
        if not self.enabled:
            return False

        try:
            serialized = self._serialize(value)
            self.redis_client.setex(key, ttl, serialized)
            logger.debug(f"Cache SET: {key} (TTL: {ttl}s)")
            return True
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {str(e)}")
            return False

    def delete(self, key: str) -> bool:
        """Delete a specific cache key"""
        if not self.enabled:
            return False

        try:
            self.redis_client.delete(key)
            logger.debug(f"Cache DELETE: {key}")
            return True
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {str(e)}")
            return False

    def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching a pattern
        Example: delete_pattern('course:*') deletes all course caches
        """
        if not self.enabled:
            return 0

        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                deleted = self.redis_client.delete(*keys)
                logger.info(f"Cache DELETE PATTERN: {pattern} ({deleted} keys)")
                return deleted
            return 0
        except Exception as e:
            logger.error(f"Cache delete pattern error for {pattern}: {str(e)}")
            return 0

    def invalidate_course(self, course_id: str):
        """Invalidate all cache related to a course"""
        patterns = [
            f'course:{course_id}',
            f'course:{course_id}:*',
            f'lessons:course:{course_id}',
            f'lessons:course:{course_id}:*',
            'courses:all:*',  # Invalidate course listings
            'stats'  # Invalidate stats
        ]
        for pattern in patterns:
            self.delete_pattern(pattern)

    def invalidate_lesson(self, lesson_id: str, course_id: str = None):
        """Invalidate all cache related to a lesson"""
        patterns = [
            f'lesson:{lesson_id}',
            f'lesson:{lesson_id}:*',
            f'files:lesson:{lesson_id}:*',
        ]
        if course_id:
            patterns.append(f'lessons:course:{course_id}:*')
            patterns.append(f'course:{course_id}:*')

        for pattern in patterns:
            self.delete_pattern(pattern)

    def invalidate_file(self, file_id: str, lesson_id: str = None):
        """Invalidate all cache related to a file"""
        patterns = [
            f'file:{file_id}:*',
        ]
        if lesson_id:
            patterns.append(f'files:lesson:{lesson_id}:*')
            patterns.append(f'lesson:{lesson_id}:*')

        for pattern in patterns:
            self.delete_pattern(pattern)

    def invalidate_user_progress(self, user_id: str, file_id: str = None, course_id: str = None):
        """Invalidate user progress cache"""
        patterns = []

        if file_id:
            patterns.append(f'progress:{user_id}:{file_id}')
            patterns.append(f'file:{file_id}:{user_id}')

        if course_id:
            patterns.append(f'course_progress:{user_id}:{course_id}')
            patterns.append(f'course:{course_id}:{user_id}')
            patterns.append(f'lessons:course:{course_id}:{user_id}')

        # Invalidate course listings with progress
        patterns.append(f'courses:all:{user_id}')

        for pattern in patterns:
            self.delete_pattern(pattern)

    def clear_all(self):
        """Clear entire cache (use with caution)"""
        if not self.enabled:
            return

        try:
            self.redis_client.flushdb()
            logger.warning("Cache cleared: All keys deleted")
        except Exception as e:
            logger.error(f"Cache clear error: {str(e)}")

    def get_stats(self) -> dict:
        """Get cache statistics"""
        if not self.enabled:
            return {'enabled': False}

        try:
            info = self.redis_client.info('stats')
            return {
                'enabled': True,
                'total_keys': self.redis_client.dbsize(),
                'hits': info.get('keyspace_hits', 0),
                'misses': info.get('keyspace_misses', 0),
                'hit_rate': self._calculate_hit_rate(
                    info.get('keyspace_hits', 0),
                    info.get('keyspace_misses', 0)
                )
            }
        except Exception as e:
            logger.error(f"Failed to get cache stats: {str(e)}")
            return {'enabled': False, 'error': str(e)}

    def _calculate_hit_rate(self, hits: int, misses: int) -> float:
        """Calculate cache hit rate percentage"""
        total = hits + misses
        if total == 0:
            return 0.0
        return round((hits / total) * 100, 2)


# Global cache instance
_cache = None

def get_cache() -> CacheService:
    """Get or create global cache instance"""
    global _cache
    if _cache is None:
        _cache = CacheService()
    return _cache


def cached(key_prefix: str, ttl: int = 300, user_specific: bool = False):
    """
    Decorator to cache function results

    Args:
        key_prefix: Prefix for cache key
        ttl: Time to live in seconds (default 5 minutes)
        user_specific: If True, includes user_id in cache key

    Example:
        @cached('course', ttl=600, user_specific=True)
        def get_course_by_id(course_id, user_id='default_user'):
            # Your code here
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache = get_cache()

            # Build cache key
            key_parts = [key_prefix]

            # Add positional arguments to key
            key_parts.extend(str(arg) for arg in args)

            # Add user_id if user_specific
            if user_specific:
                user_id = kwargs.get('user_id', 'default_user')
                key_parts.append(user_id)

            cache_key = ':'.join(key_parts)

            # Try to get from cache
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result

            # Call original function
            result = func(*args, **kwargs)

            # Cache the result
            if result is not None:
                cache.set(cache_key, result, ttl)

            return result

        return wrapper
    return decorator


if __name__ == '__main__':
    # Test Redis connection
    cache = CacheService()
    if cache.enabled:
        print("✓ Redis cache is working!")
        print(f"Stats: {cache.get_stats()}")
    else:
        print("✗ Redis cache is not available")
