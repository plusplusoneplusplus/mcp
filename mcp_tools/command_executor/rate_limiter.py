import time
import asyncio
from typing import Dict, Optional, Tuple
from datetime import datetime, UTC
from collections import defaultdict, deque
import logging

from .types import RateLimitConfig, RateLimitStatus

logger = logging.getLogger(__name__)


class TokenBucket:
    """Token bucket implementation for rate limiting"""
    
    def __init__(self, capacity: int, refill_rate: float):
        """
        Initialize token bucket
        
        Args:
            capacity: Maximum number of tokens in bucket
            refill_rate: Tokens added per second
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = float(capacity)
        self.last_refill = time.time()
        self._lock = asyncio.Lock()
    
    async def consume(self, tokens: int = 1) -> bool:
        """
        Try to consume tokens from bucket
        
        Args:
            tokens: Number of tokens to consume
            
        Returns:
            True if tokens were consumed, False if not enough tokens
        """
        async with self._lock:
            self._refill()
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False
    
    def _refill(self) -> None:
        """Refill tokens based on elapsed time"""
        now = time.time()
        elapsed = now - self.last_refill
        
        # Add tokens based on elapsed time
        tokens_to_add = elapsed * self.refill_rate
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now
    
    async def get_status(self) -> Dict[str, float]:
        """Get current bucket status"""
        async with self._lock:
            self._refill()
            return {
                "tokens": self.tokens,
                "capacity": self.capacity,
                "refill_rate": self.refill_rate
            }


class SlidingWindowRateLimiter:
    """Sliding window rate limiter implementation"""
    
    def __init__(self, window_size: int, max_requests: int):
        """
        Initialize sliding window rate limiter
        
        Args:
            window_size: Window size in seconds
            max_requests: Maximum requests per window
        """
        self.window_size = window_size
        self.max_requests = max_requests
        self.requests: Dict[str, deque] = defaultdict(deque)
        self._lock = asyncio.Lock()
    
    async def is_allowed(self, user_id: str) -> Tuple[bool, int]:
        """
        Check if request is allowed for user
        
        Args:
            user_id: User identifier
            
        Returns:
            Tuple of (is_allowed, requests_in_window)
        """
        async with self._lock:
            now = time.time()
            user_requests = self.requests[user_id]
            
            # Remove old requests outside the window
            while user_requests and user_requests[0] <= now - self.window_size:
                user_requests.popleft()
            
            requests_in_window = len(user_requests)
            
            if requests_in_window < self.max_requests:
                user_requests.append(now)
                return True, requests_in_window + 1
            
            return False, requests_in_window
    
    async def get_status(self, user_id: str) -> Dict[str, int]:
        """Get rate limit status for user"""
        async with self._lock:
            now = time.time()
            user_requests = self.requests[user_id]
            
            # Remove old requests
            while user_requests and user_requests[0] <= now - self.window_size:
                user_requests.popleft()
            
            requests_in_window = len(user_requests)
            
            # Calculate when window resets (oldest request + window_size)
            window_reset_time = None
            if user_requests:
                window_reset_time = user_requests[0] + self.window_size
            
            return {
                "requests_in_window": requests_in_window,
                "max_requests": self.max_requests,
                "requests_remaining": max(0, self.max_requests - requests_in_window),
                "window_reset_time": window_reset_time
            }


class RateLimiter:
    """Combined rate limiter with token bucket and sliding window"""
    
    def __init__(self, config: RateLimitConfig):
        """
        Initialize rate limiter
        
        Args:
            config: Rate limiting configuration
        """
        self.config = config
        self.enabled = config.enabled
        
        if self.enabled:
            # Per-user token buckets for burst control
            self.token_buckets: Dict[str, TokenBucket] = {}
            self.bucket_lock = asyncio.Lock()
            
            # Sliding window for overall rate limiting
            self.sliding_window = SlidingWindowRateLimiter(
                window_size=config.window_seconds,
                max_requests=config.requests_per_minute
            )
        
        logger.info(f"RateLimiter initialized: enabled={self.enabled}, "
                   f"requests_per_minute={config.requests_per_minute}, "
                   f"burst_size={config.burst_size}")
    
    async def _get_user_bucket(self, user_id: str) -> TokenBucket:
        """Get or create token bucket for user"""
        async with self.bucket_lock:
            if user_id not in self.token_buckets:
                self.token_buckets[user_id] = TokenBucket(
                    capacity=self.config.burst_size,
                    refill_rate=self.config.requests_per_minute / 60.0
                )
            return self.token_buckets[user_id]
    
    async def check_rate_limit(self, user_id: str) -> Tuple[bool, Optional[Dict]]:
        """
        Check if request is allowed for user
        
        Args:
            user_id: User identifier
            
        Returns:
            Tuple of (is_allowed, error_info)
        """
        if not self.enabled:
            return True, None
        
        # Check sliding window first
        window_allowed, requests_in_window = await self.sliding_window.is_allowed(user_id)
        
        if not window_allowed:
            # Calculate retry after time
            window_status = await self.sliding_window.get_status(user_id)
            retry_after = int(window_status.get("window_reset_time", time.time()) - time.time())
            retry_after = max(1, retry_after)  # At least 1 second
            
            error_info = {
                "error": "rate_limited",
                "message": "Too many requests",
                "retry_after": retry_after,
                "limits": {
                    "requests_per_minute": self.config.requests_per_minute,
                    "current_usage": requests_in_window,
                    "window_seconds": self.config.window_seconds
                }
            }
            return False, error_info
        
        # Check token bucket for burst control
        user_bucket = await self._get_user_bucket(user_id)
        bucket_allowed = await user_bucket.consume(1)
        
        if not bucket_allowed:
            # Calculate retry after based on refill rate
            bucket_status = await user_bucket.get_status()
            tokens_needed = 1 - bucket_status["tokens"]
            retry_after = max(1, int(tokens_needed / bucket_status["refill_rate"]))
            
            error_info = {
                "error": "rate_limited",
                "message": "Burst limit exceeded",
                "retry_after": retry_after,
                "limits": {
                    "burst_size": self.config.burst_size,
                    "current_tokens": bucket_status["tokens"],
                    "refill_rate": bucket_status["refill_rate"]
                }
            }
            return False, error_info
        
        return True, None
    
    async def get_rate_limit_status(self, user_id: str) -> RateLimitStatus:
        """Get current rate limit status for user"""
        if not self.enabled:
            # Return unlimited status when disabled
            return RateLimitStatus(
                requests_remaining=999999,
                requests_per_minute=999999,
                window_reset_time=datetime.now(UTC),
                burst_remaining=999999
            )
        
        window_status = await self.sliding_window.get_status(user_id)
        user_bucket = await self._get_user_bucket(user_id)
        bucket_status = await user_bucket.get_status()
        
        # Calculate window reset time
        window_reset_time = datetime.now(UTC)
        if window_status.get("window_reset_time"):
            window_reset_time = datetime.fromtimestamp(
                window_status["window_reset_time"], tz=UTC
            )
        
        return RateLimitStatus(
            requests_remaining=window_status["requests_remaining"],
            requests_per_minute=self.config.requests_per_minute,
            window_reset_time=window_reset_time,
            burst_remaining=int(bucket_status["tokens"])
        )
    
    def update_config(self, config: RateLimitConfig) -> None:
        """Update rate limiter configuration"""
        self.config = config
        self.enabled = config.enabled
        
        if self.enabled:
            # Clear existing token buckets to apply new config
            self.token_buckets.clear()
            
            # Update sliding window
            self.sliding_window.window_size = config.window_seconds
            self.sliding_window.max_requests = config.requests_per_minute
        
        logger.info(f"RateLimiter config updated: enabled={self.enabled}") 