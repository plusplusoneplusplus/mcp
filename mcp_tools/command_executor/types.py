from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel

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