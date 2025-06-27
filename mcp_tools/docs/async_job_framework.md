# Async Job Framework

## Problem Statement

Currently, long-running operations in MCP tools follow an ad-hoc pattern where:
1. A command executor starts a job and returns a token
2. Clients use separate tools to poll job status using the token
3. This pattern is repeated across different tools without standardization

This leads to code duplication, inconsistent interfaces, and maintenance overhead.

## Framework Architecture

### Core Components

1. **Job Manager**: Central coordinator for all async jobs
2. **Job Interface**: Standard contract for executable jobs
3. **Token System**: Secure job identification and tracking
4. **Status Tracker**: Unified status reporting mechanism
5. **Result Store**: Temporary storage for job outputs

### Job Lifecycle States

```
QUEUED -> RUNNING -> COMPLETED
           |
           v
       FAILED/CANCELLED
```

## Core Interfaces

### AsyncJob (Abstract Base Class)
```python
from abc import ABC, abstractmethod
from typing import Any, Optional
import asyncio
from enum import Enum

class JobState(Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class JobResult:
    success: bool
    data: Any = None
    error: Optional[str] = None
    metadata: dict = field(default_factory=dict)

@dataclass
class JobProgress:
    current: int
    total: int
    message: Optional[str] = None

    @property
    def percentage(self) -> float:
        return (self.current / self.total) * 100 if self.total > 0 else 0

class AsyncJob(ABC):
    def __init__(self, job_id: str):
        self.id = job_id
        self.state = JobState.QUEUED
        self._cancel_event = asyncio.Event()

    @abstractmethod
    async def execute(self) -> JobResult:
        """Execute the job and return result"""
        pass

    async def cancel(self) -> None:
        """Cancel the job"""
        self._cancel_event.set()
        self.state = JobState.CANCELLED

    def get_progress(self) -> JobProgress:
        """Get current job progress"""
        return JobProgress(0, 1, "No progress tracking")

    @property
    def is_cancelled(self) -> bool:
        return self._cancel_event.is_set()
```

### JobManager
```python
from typing import Dict, List
import asyncio
import uuid
from datetime import datetime, timedelta

class JobManager:
    def __init__(self, max_concurrent_jobs: int = 10):
        self._jobs: Dict[str, AsyncJob] = {}
        self._results: Dict[str, JobResult] = {}
        self._semaphore = asyncio.Semaphore(max_concurrent_jobs)
        self._cleanup_task: Optional[asyncio.Task] = None

    async def submit(self, job: AsyncJob) -> str:
        """Submit a job and return token"""
        token = str(uuid.uuid4())
        self._jobs[token] = job

        # Start job execution in background
        asyncio.create_task(self._execute_job(token, job))
        return token

    async def get_status(self, token: str) -> dict:
        """Get job status by token"""
        if token not in self._jobs:
            raise ValueError(f"Job {token} not found")

        job = self._jobs[token]
        return {
            "token": token,
            "state": job.state.value,
            "progress": job.get_progress().__dict__
        }

    async def get_result(self, token: str) -> JobResult:
        """Get job result by token"""
        if token not in self._results:
            raise ValueError(f"Result for job {token} not available")

        return self._results[token]

    async def cancel_job(self, token: str) -> None:
        """Cancel a job by token"""
        if token in self._jobs:
            await self._jobs[token].cancel()

    async def list_jobs(self) -> List[dict]:
        """List all jobs with their status"""
        return [
            {
                "token": token,
                "state": job.state.value,
                "id": job.id
            }
            for token, job in self._jobs.items()
        ]

    async def _execute_job(self, token: str, job: AsyncJob) -> None:
        """Execute job with concurrency control"""
        async with self._semaphore:
            try:
                job.state = JobState.RUNNING
                result = await job.execute()
                job.state = JobState.COMPLETED
                self._results[token] = result
            except Exception as e:
                job.state = JobState.FAILED
                self._results[token] = JobResult(
                    success=False,
                    error=str(e)
                )
```

### JobStore (Abstract Base Class)
```python
class JobStore(ABC):
    @abstractmethod
    async def store(self, token: str, result: JobResult) -> None:
        """Store job result"""
        pass

    @abstractmethod
    async def retrieve(self, token: str) -> JobResult:
        """Retrieve job result"""
        pass

    @abstractmethod
    async def cleanup(self, token: str) -> None:
        """Clean up job result"""
        pass

class InMemoryJobStore(JobStore):
    def __init__(self):
        self._store: Dict[str, JobResult] = {}

    async def store(self, token: str, result: JobResult) -> None:
        self._store[token] = result

    async def retrieve(self, token: str) -> JobResult:
        if token not in self._store:
            raise ValueError(f"Result for token {token} not found")
        return self._store[token]

    async def cleanup(self, token: str) -> None:
        self._store.pop(token, None)
```

## Implementation Patterns

### Tool Integration
```python
# Instead of custom async handling
class CommandExecutorTool:
    def __init__(self, job_manager: JobManager):
        self.job_manager = job_manager

    async def execute_command(self, cmd: str) -> str:
        """Execute command and return job token"""
        job = CommandJob(cmd)
        token = await self.job_manager.submit(job)
        return token

class JobStatusTool:
    def __init__(self, job_manager: JobManager):
        self.job_manager = job_manager

    async def get_status(self, token: str) -> dict:
        """Get job status by token"""
        return await self.job_manager.get_status(token)

    async def get_result(self, token: str) -> JobResult:
        """Get job result by token"""
        return await self.job_manager.get_result(token)
```

### Job Implementation
```python
import asyncio
import subprocess

class CommandJob(AsyncJob):
    def __init__(self, command: str):
        super().__init__(f"cmd_{command[:20]}")
        self.command = command
        self.process: Optional[asyncio.subprocess.Process] = None

    async def execute(self) -> JobResult:
        """Execute long-running command"""
        try:
            # Check for cancellation before starting
            if self.is_cancelled:
                return JobResult(success=False, error="Job cancelled")

            # Start process
            self.process = await asyncio.create_subprocess_shell(
                self.command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            # Wait for completion or cancellation
            stdout, stderr = await self.process.communicate()

            if self.process.returncode == 0:
                return JobResult(
                    success=True,
                    data=stdout.decode(),
                    metadata={"command": self.command}
                )
            else:
                return JobResult(
                    success=False,
                    error=stderr.decode(),
                    metadata={"command": self.command, "exit_code": self.process.returncode}
                )

        except Exception as e:
            return JobResult(success=False, error=str(e))

    async def cancel(self) -> None:
        """Cancel the running command"""
        await super().cancel()
        if self.process and self.process.returncode is None:
            self.process.terminate()
            try:
                await asyncio.wait_for(self.process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self.process.kill()
```

## Configuration Options

### Job Timeouts
- Default timeout: 5 minutes
- Configurable per job type
- Automatic cleanup of expired jobs

### Storage Strategy
- In-memory for short jobs (< 1 minute)
- Persistent storage for longer jobs
- Configurable retention policies

### Concurrency Control
- Max concurrent jobs per tool
- Priority queue support
- Resource-based throttling

## Security Considerations

### Token Security
- Cryptographically secure tokens
- Time-limited validity
- Client-scoped access control

### Resource Protection
- Memory usage limits
- CPU throttling for background jobs
- Disk space management

## Error Handling

### Job Failures
- Structured error reporting
- Retry mechanisms for transient failures
- Dead letter queue for failed jobs

### System Failures
- Job recovery after restarts
- Graceful degradation
- Health check endpoints

## Usage Examples

### Basic Job Submission
```python
# Tool submits job
job_manager = JobManager()
token = await job_manager.submit(DataProcessingJob(data))

# Client polls for completion
status = await job_manager.get_status(token)
if status["state"] == "completed":
    result = await job_manager.get_result(token)
```

### Progress Monitoring
```python
import asyncio

async def monitor_job(job_manager: JobManager, token: str):
    while True:
        status = await job_manager.get_status(token)
        progress = status["progress"]
        print(f"Progress: {progress['percentage']:.1f}% - {progress['message']}")

        if status["state"] not in ["queued", "running"]:
            break

        await asyncio.sleep(1)

# Usage
token = await job_manager.submit(job)
await monitor_job(job_manager, token)
```

### MCP Tool Integration
```python
from mcp_tools.core import Tool, ToolInterface

class AsyncCommandTool(Tool):
    def __init__(self, job_manager: JobManager):
        self.job_manager = job_manager

    async def execute_command_async(self, command: str) -> dict:
        """Execute command asynchronously and return job token"""
        job = CommandJob(command)
        token = await self.job_manager.submit(job)
        return {"token": token, "message": f"Command '{command}' submitted"}

    async def get_job_status(self, token: str) -> dict:
        """Get status of async job"""
        try:
            return await self.job_manager.get_status(token)
        except ValueError as e:
            return {"error": str(e)}

    async def get_job_result(self, token: str) -> dict:
        """Get result of completed job"""
        try:
            result = await self.job_manager.get_result(token)
            return {
                "success": result.success,
                "data": result.data,
                "error": result.error,
                "metadata": result.metadata
            }
        except ValueError as e:
            return {"error": str(e)}
```

## Benefits

### For Tool Developers
- Consistent async patterns across all tools
- Built-in progress tracking and cancellation
- Automatic cleanup and resource management
- Standardized error handling

### For MCP Clients
- Uniform interface for all long-running operations
- Predictable status checking mechanism
- Ability to manage multiple concurrent jobs
- Better resource utilization

### For System Architecture
- Centralized job management and monitoring
- Improved scalability and resource control
- Easier debugging and troubleshooting
- Standardized metrics and logging

## Migration Strategy

1. **Phase 1**: Implement core framework alongside existing tools
2. **Phase 2**: Migrate high-value tools to use framework
3. **Phase 3**: Deprecate custom async implementations
4. **Phase 4**: Remove legacy async code

## Extension Points

### Custom Job Types
- Batch processing jobs
- Streaming data jobs
- Scheduled recurring jobs
- Dependent job chains

### Monitoring Integration
- Metrics collection hooks
- Custom progress reporters
- External monitoring system integration
- Performance analytics

This framework would provide a robust, scalable foundation for all async operations in the MCP tools ecosystem while maintaining backward compatibility during migration.

## Implementation Todo

### Phase 1: Core Framework (High Priority) ✅ COMPLETED
- [x] Implement `AsyncJob` abstract base class with cancellation support
- [x] Create `JobManager` with concurrency control and background execution
- [x] Build `JobResult` and `JobProgress` data structures
- [x] Add `InMemoryJobStore` implementation
- [x] Create unit tests for core components
- [x] Add basic error handling and logging

### Phase 2: Tool Integration (High Priority)
- [ ] Create `AsyncCommandTool` as reference implementation
- [ ] Add job status and result retrieval tools
- [ ] Implement proper MCP tool interface integration
- [ ] Add configuration system for timeouts and limits
- [ ] Create integration tests with real commands

### Phase 3: Advanced Features (Medium Priority)
- [ ] Add persistent storage backend (SQLite/Redis)
- [ ] Implement job progress tracking for long-running tasks
- [ ] Add job priority queue system
- [ ] Create job dependency chains
- [ ] Add metrics collection and monitoring hooks
- [ ] Implement job scheduling and recurring jobs

### Phase 4: Production Features (Medium Priority)
- [ ] Add comprehensive logging and debugging
- [ ] Implement health check endpoints
- [ ] Add job cleanup and retention policies
- [ ] Create performance benchmarks
- [ ] Add resource usage monitoring (memory, CPU)
- [ ] Implement graceful shutdown handling

### Phase 5: Migration & Documentation (Low Priority)
- [ ] Create migration guide for existing tools
- [ ] Add comprehensive API documentation
- [ ] Create example implementations for common patterns
- [ ] Add troubleshooting guide
- [ ] Performance optimization based on real usage
- [ ] Deprecation plan for legacy async implementations

### Technical Debt & Maintenance
- [ ] Add type hints throughout codebase
- [ ] Set up automated testing pipeline
- [ ] Add code coverage reporting
- [ ] Create performance regression tests
- [ ] Add security audit for token handling
- [ ] Review and optimize memory usage patterns
