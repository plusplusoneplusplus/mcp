"""Task management examples and demonstrations.

This package contains practical examples showing how to use the Neo4j graph interface
for task management scenarios including:

- Basic task creation and dependency modeling
- Complex workflows with multiple dependency types
- Resource constraint modeling
- Task priority and scheduling
- Error handling and recovery scenarios
"""

from .task_example import TaskExample
from .basic_usage import BasicUsageExample
from .advanced_queries import AdvancedQueriesExample
from .resource_management import ResourceManagementExample

__all__ = [
    "TaskExample",
    "BasicUsageExample", 
    "AdvancedQueriesExample",
    "ResourceManagementExample",
] 