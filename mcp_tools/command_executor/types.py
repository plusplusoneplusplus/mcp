from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field
from datetime import datetime


class CommandResult(BaseModel):
    """Result of a command execution"""

    success: bool
    return_code: int
    output: str
    error: str


class AsyncCommandResponse(BaseModel):
    """Response from starting an asynchronous command"""

    token: str
    status: str
    pid: Optional[int] = None
    error: Optional[str] = None


class ProcessStatusResponse(BaseModel):
    """Status of an asynchronous process"""

    status: str
    pid: Optional[int] = None
    token: Optional[str] = None
    command: Optional[str] = None
    runtime: Optional[float] = None
    cpu_percent: Optional[float] = None
    memory_info: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class ProcessCompletedResponse(BaseModel):
    """Final result of a completed process"""

    status: str = "completed"
    success: bool
    return_code: int
    output: str
    error: str
    pid: int


class RateLimitConfig(BaseModel):
    """Configuration for rate limiting"""
    
    requests_per_minute: int = Field(default=60, ge=1, description="Maximum requests per minute")
    burst_size: int = Field(default=10, ge=1, description="Maximum burst requests allowed")
    window_seconds: int = Field(default=60, ge=1, description="Rate limit window in seconds")
    enabled: bool = Field(default=True, description="Whether rate limiting is enabled")


class ConcurrencyConfig(BaseModel):
    """Configuration for concurrency control"""
    
    max_concurrent_processes: int = Field(default=10, ge=1, description="Maximum concurrent processes")
    max_processes_per_user: int = Field(default=5, ge=1, description="Maximum processes per user")
    process_queue_size: int = Field(default=50, ge=0, description="Maximum queued requests")
    enabled: bool = Field(default=True, description="Whether concurrency control is enabled")


class ResourceLimitConfig(BaseModel):
    """Configuration for resource limits"""
    
    max_memory_per_process_mb: int = Field(default=512, ge=1, description="Memory limit per process in MB")
    max_cpu_time_seconds: int = Field(default=300, ge=1, description="CPU time limit in seconds")
    max_execution_time_seconds: int = Field(default=600, ge=1, description="Wall clock time limit in seconds")
    enabled: bool = Field(default=True, description="Whether resource limits are enabled")


class ExecutorConfig(BaseModel):
    """Complete configuration for CommandExecutor"""
    
    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig)
    concurrency: ConcurrencyConfig = Field(default_factory=ConcurrencyConfig)
    resource_limits: ResourceLimitConfig = Field(default_factory=ResourceLimitConfig)


class RateLimitError(BaseModel):
    """Response when rate limited"""
    
    error: str = "rate_limited"
    message: str = "Too many requests"
    retry_after: int = Field(description="Seconds to wait before retrying")
    limits: Dict[str, Any] = Field(description="Current rate limit information")


class ConcurrencyLimitError(BaseModel):
    """Response when concurrency limited"""
    
    error: str = "concurrency_limited"
    message: str = "Too many concurrent processes"
    queue_position: Optional[int] = Field(default=None, description="Position in queue if queued")
    estimated_wait_seconds: Optional[int] = Field(default=None, description="Estimated wait time")


class QueueStatus(BaseModel):
    """Status of the process queue"""
    
    queue_size: int = Field(description="Current number of queued requests")
    max_queue_size: int = Field(description="Maximum queue size")
    processing: int = Field(description="Number of currently processing requests")
    max_concurrent: int = Field(description="Maximum concurrent processes")


class RateLimitStatus(BaseModel):
    """Current rate limit status"""
    
    requests_remaining: int = Field(description="Requests remaining in current window")
    requests_per_minute: int = Field(description="Maximum requests per minute")
    window_reset_time: datetime = Field(description="When the current window resets")
    burst_remaining: int = Field(description="Burst requests remaining")


class UserLimits(BaseModel):
    """Per-user limits and current usage"""
    
    user_id: str = Field(description="User identifier")
    concurrent_processes: int = Field(description="Current concurrent processes for user")
    max_concurrent_processes: int = Field(description="Maximum concurrent processes for user")
    rate_limit_status: RateLimitStatus = Field(description="Rate limit status for user")
