"""
Workflow Definition

Parse, validate, and represent workflow definitions from YAML files.
"""

import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class WorkflowInput:
    """Workflow input parameter definition."""

    name: str
    type: str = "string"
    required: bool = False
    default: Any = None
    description: str = ""

    @classmethod
    def from_dict(cls, name: str, data: Dict[str, Any]) -> "WorkflowInput":
        """Create from dictionary."""
        return cls(
            name=name,
            type=data.get("type", "string"),
            required=data.get("required", False),
            default=data.get("default"),
            description=data.get("description", ""),
        )


@dataclass
class WorkflowOutput:
    """Workflow output definition."""

    name: str
    type: str = "string"
    description: str = ""

    @classmethod
    def from_dict(cls, name: str, data: Dict[str, Any]) -> "WorkflowOutput":
        """Create from dictionary."""
        return cls(
            name=name,
            type=data.get("type", "string"),
            description=data.get("description", ""),
        )


@dataclass
class StepDefinition:
    """Workflow step definition."""

    id: str
    type: str
    depends_on: List[str] = field(default_factory=list)
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, str] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)

    # Agent step specific
    agent: Optional[str] = None
    operation: Optional[str] = None

    # Conditional step specific
    condition: Optional[str] = None
    then_steps: List["StepDefinition"] = field(default_factory=list)
    else_steps: List["StepDefinition"] = field(default_factory=list)

    # Parallel step specific
    parallel_steps: List["StepDefinition"] = field(default_factory=list)
    max_concurrency: Optional[int] = None

    # Loop step specific
    items: Optional[str] = None
    item_var: Optional[str] = None
    loop_steps: List["StepDefinition"] = field(default_factory=list)

    # Transform step specific
    script: Optional[str] = None

    # Error handling
    retry: Optional[Dict[str, Any]] = None
    timeout: Optional[int] = None
    on_error: str = "stop"  # stop, continue, retry

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StepDefinition":
        """
        Create from dictionary.

        Args:
            data: Step definition dictionary

        Returns:
            StepDefinition instance
        """
        step_id = data.get("id", "")
        step_type = data.get("type", "")

        # Base fields
        step = cls(
            id=step_id,
            type=step_type,
            depends_on=data.get("depends_on", []),
            inputs=data.get("inputs", {}),
            outputs=data.get("outputs", {}),
            config=data.get("config", {}),
            retry=data.get("retry"),
            timeout=data.get("timeout"),
            on_error=data.get("on_error", "stop"),
        )

        # Type-specific fields
        if step_type == "agent":
            step.agent = data.get("agent")
            step.operation = data.get("operation")
        elif step_type == "conditional":
            step.condition = data.get("condition")
            step.then_steps = [
                cls.from_dict(s) for s in data.get("then", [])
            ]
            step.else_steps = [
                cls.from_dict(s) for s in data.get("else", [])
            ]
        elif step_type == "parallel":
            step.parallel_steps = [
                cls.from_dict(s) for s in data.get("steps", [])
            ]
            step.max_concurrency = data.get("max_concurrency")
        elif step_type == "loop":
            step.items = data.get("items")
            step.item_var = data.get("item_var", "item")
            step.loop_steps = [
                cls.from_dict(s) for s in data.get("steps", [])
            ]
        elif step_type == "transform":
            step.script = data.get("script")

        return step

    def get_all_step_ids(self) -> List[str]:
        """
        Get all step IDs including nested steps.

        Returns:
            List of all step IDs
        """
        ids = [self.id]

        # Add nested step IDs
        for nested_step in self.then_steps + self.else_steps + self.parallel_steps + self.loop_steps:
            ids.extend(nested_step.get_all_step_ids())

        return ids


@dataclass
class WorkflowDefinition:
    """
    Workflow definition.

    Represents a complete workflow parsed from YAML.
    """

    name: str
    version: str = "1.0"
    description: str = ""
    inputs: Dict[str, WorkflowInput] = field(default_factory=dict)
    outputs: Dict[str, WorkflowOutput] = field(default_factory=dict)
    steps: List[StepDefinition] = field(default_factory=list)
    error_handling: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_yaml(cls, yaml_str: str) -> "WorkflowDefinition":
        """
        Parse workflow from YAML string.

        Args:
            yaml_str: YAML workflow definition

        Returns:
            WorkflowDefinition instance

        Raises:
            ValueError: If YAML is invalid
        """
        try:
            data = yaml.safe_load(yaml_str)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML: {e}")

        if not data or "workflow" not in data:
            raise ValueError("YAML must contain 'workflow' key")

        workflow_data = data["workflow"]
        return cls.from_dict(workflow_data)

    @classmethod
    def from_file(cls, file_path: str) -> "WorkflowDefinition":
        """
        Load workflow from YAML file.

        Args:
            file_path: Path to YAML file

        Returns:
            WorkflowDefinition instance

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If YAML is invalid
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Workflow file not found: {file_path}")

        with open(path, "r") as f:
            yaml_str = f.read()

        return cls.from_yaml(yaml_str)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowDefinition":
        """
        Create from dictionary.

        Args:
            data: Workflow definition dictionary

        Returns:
            WorkflowDefinition instance
        """
        # Parse inputs
        inputs = {}
        for name, input_data in data.get("inputs", {}).items():
            inputs[name] = WorkflowInput.from_dict(name, input_data)

        # Parse outputs
        outputs = {}
        for name, output_data in data.get("outputs", {}).items():
            outputs[name] = WorkflowOutput.from_dict(name, output_data)

        # Parse steps
        steps = [
            StepDefinition.from_dict(step_data)
            for step_data in data.get("steps", [])
        ]

        return cls(
            name=data.get("name", "unnamed"),
            version=data.get("version", "1.0"),
            description=data.get("description", ""),
            inputs=inputs,
            outputs=outputs,
            steps=steps,
            error_handling=data.get("error_handling", {}),
            metadata=data.get("metadata", {}),
        )

    def validate(self) -> List[str]:
        """
        Validate workflow definition.

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        # Check workflow name
        if not self.name:
            errors.append("Workflow must have a name")

        # Check steps
        if not self.steps:
            errors.append("Workflow must have at least one step")

        # Collect all step IDs
        step_ids = set()
        for step in self.steps:
            step_ids.update(step.get_all_step_ids())

        # Check for duplicate step IDs
        if len(step_ids) != sum(len(step.get_all_step_ids()) for step in self.steps):
            errors.append("Duplicate step IDs found")

        # Validate dependencies
        for step in self.steps:
            for dep_id in step.depends_on:
                if dep_id not in step_ids:
                    errors.append(
                        f"Step '{step.id}' depends on unknown step '{dep_id}'"
                    )

        # Validate step types
        valid_types = ["agent", "conditional", "parallel", "loop", "transform"]
        for step in self.steps:
            if step.type not in valid_types:
                errors.append(
                    f"Step '{step.id}' has invalid type '{step.type}'. "
                    f"Must be one of: {', '.join(valid_types)}"
                )

            # Type-specific validation
            if step.type == "agent":
                if not step.agent:
                    errors.append(f"Agent step '{step.id}' must specify 'agent'")
                if not step.operation:
                    errors.append(f"Agent step '{step.id}' must specify 'operation'")
            elif step.type == "conditional":
                if not step.condition:
                    errors.append(
                        f"Conditional step '{step.id}' must specify 'condition'"
                    )
            elif step.type == "parallel":
                if not step.parallel_steps:
                    errors.append(
                        f"Parallel step '{step.id}' must have at least one substep"
                    )
            elif step.type == "loop":
                if not step.items:
                    errors.append(f"Loop step '{step.id}' must specify 'items'")
                if not step.loop_steps:
                    errors.append(
                        f"Loop step '{step.id}' must have at least one substep"
                    )
            elif step.type == "transform":
                if not step.script:
                    errors.append(f"Transform step '{step.id}' must specify 'script'")

        return errors

    def get_step(self, step_id: str) -> Optional[StepDefinition]:
        """
        Get step by ID.

        Args:
            step_id: Step identifier

        Returns:
            StepDefinition or None if not found
        """
        for step in self.steps:
            if step.id == step_id:
                return step
            # Check nested steps
            for nested in step.then_steps + step.else_steps + step.parallel_steps + step.loop_steps:
                if nested.id == step_id:
                    return nested
        return None

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "inputs": {
                name: {
                    "type": inp.type,
                    "required": inp.required,
                    "default": inp.default,
                    "description": inp.description,
                }
                for name, inp in self.inputs.items()
            },
            "outputs": {
                name: {"type": out.type, "description": out.description}
                for name, out in self.outputs.items()
            },
            "steps": [self._step_to_dict(step) for step in self.steps],
            "error_handling": self.error_handling,
            "metadata": self.metadata,
        }

    def _step_to_dict(self, step: StepDefinition) -> Dict[str, Any]:
        """Convert step to dictionary."""
        result = {
            "id": step.id,
            "type": step.type,
        }

        if step.depends_on:
            result["depends_on"] = step.depends_on
        if step.inputs:
            result["inputs"] = step.inputs
        if step.outputs:
            result["outputs"] = step.outputs
        if step.config:
            result["config"] = step.config

        # Type-specific fields
        if step.type == "agent":
            result["agent"] = step.agent
            result["operation"] = step.operation
        elif step.type == "conditional":
            result["condition"] = step.condition
            if step.then_steps:
                result["then"] = [self._step_to_dict(s) for s in step.then_steps]
            if step.else_steps:
                result["else"] = [self._step_to_dict(s) for s in step.else_steps]
        elif step.type == "parallel":
            result["steps"] = [self._step_to_dict(s) for s in step.parallel_steps]
            if step.max_concurrency:
                result["max_concurrency"] = step.max_concurrency
        elif step.type == "loop":
            result["items"] = step.items
            result["item_var"] = step.item_var
            result["steps"] = [self._step_to_dict(s) for s in step.loop_steps]
        elif step.type == "transform":
            result["script"] = step.script

        # Error handling
        if step.retry:
            result["retry"] = step.retry
        if step.timeout:
            result["timeout"] = step.timeout
        if step.on_error != "stop":
            result["on_error"] = step.on_error

        return result

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"WorkflowDefinition(name='{self.name}', "
            f"version='{self.version}', steps={len(self.steps)})"
        )
