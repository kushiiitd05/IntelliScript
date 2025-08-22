import redis
import json
import hashlib
import os
from typing import Any, Optional

class CacheManager:
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        try:
            self.client = redis.from_url(self.redis_url, decode_responses=True)
            self.client.ping()
            print("✅ Connected to Redis cache")
        except Exception as e:
            print(f"⚠️ Redis not available: {e}")
            self.client = None
    
    def _generate_key(self, prefix: str, identifier: str) -> str:
        """Generate a cache key"""
        hash_id = hashlib.md5(identifier.encode()).hexdigest()
        return f"{prefix}:{hash_id}"
    
    def get_cached_result(self, url: str) -> Optional[dict]:
        """Get cached result for a URL"""
        if not self.client:
            return None
        
        try:
            key = self._generate_key("transcript", url)
            cached_data = self.client.get(key)
            if cached_data:
                return json.loads(cached_data)
        except Exception as e:
            print(f"Cache get error: {e}")
        return None
    
    def cache_result(self, url: str, result: dict, ttl: int = 86400):
        """Cache a result with TTL (default 24 hours)"""
        if not self.client:
            return
        
        try:
            key = self._generate_key("transcript", url)
            self.client.setex(key, ttl, json.dumps(result))
            print(f"✅ Cached result for: {url[:50]}...")
        except Exception as e:
            print(f"Cache set error: {e}")
    
    def get_session_data(self, session_id: str) -> Optional[dict]:
        """Get session data"""
        if not self.client:
            return None
        
        try:
            key = f"session:{session_id}"
            cached_data = self.client.get(key)
            if cached_data:
                return json.loads(cached_data)
        except Exception as e:
            print(f"Session get error: {e}")
        return None
    
    def set_session_data(self, session_id: str, data: dict, ttl: int = 3600):
        """Set session data with TTL (default 1 hour)"""
        if not self.client:
            return
        
        try:
            key = f"session:{session_id}"
            self.client.setex(key, ttl, json.dumps(data))
        except Exception as e:
            print(f"Session set error: {e}")