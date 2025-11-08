"""Base operation class and registry for transform operations."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Type, Optional


class BaseOperation(ABC):
    """
    Base class for transform operations.

    All operations should inherit from this class and implement:
    - validate(): Check if inputs/config are valid
    - execute(): Perform the transformation
    """

    def __init__(self, config: Dict[str, Any], inputs: Dict[str, Any]):
        """
        Initialize operation.

        Args:
            config: Operation configuration from step definition
            inputs: Resolved inputs from workflow context
        """
        self.config = config
        self.inputs = inputs

    @abstractmethod
    def validate(self) -> Optional[str]:
        """
        Validate operation configuration and inputs.

        Returns:
            Error message if invalid, None if valid
        """
        pass

    @abstractmethod
    async def execute(self) -> Dict[str, Any]:
        """
        Execute the operation.

        Returns:
            Result dictionary
        """
        pass


class OperationRegistry:
    """Registry for transform operations."""

    def __init__(self):
        """Initialize operation registry."""
        self._operations: Dict[str, Type[BaseOperation]] = {}

    def register(self, name: str, operation_class: Type[BaseOperation]):
        """
        Register an operation.

        Args:
            name: Operation name
            operation_class: Operation class
        """
        self._operations[name] = operation_class

    def get(self, name: str) -> Optional[Type[BaseOperation]]:
        """
        Get operation class by name.

        Args:
            name: Operation name

        Returns:
            Operation class or None if not found
        """
        return self._operations.get(name)

    def list_operations(self) -> list[str]:
        """
        List all registered operations.

        Returns:
            List of operation names
        """
        return list(self._operations.keys())
