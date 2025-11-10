"""AI-powered split operation for intelligent task decomposition."""

import json
import logging
from typing import Any, Dict, Optional, List

from .base import BaseOperation


class AISplitOperation(BaseOperation):
    """
    AI-powered task splitting operation.

    Uses an AI model to intelligently decompose a high-level exploration goal into
    smaller, focused sub-tasks. The AI decides what aspects to explore, how to
    organize the work, and how many parallel tasks to create.

    Unlike the deterministic split operation, this uses AI reasoning to:
    - Understand the exploration goal
    - Identify key areas to investigate
    - Break down into logical, focused sub-tasks
    - Determine optimal task granularity

    Config:
        - model: AI model to use for splitting (default: haiku for speed)
        - max_tasks: Maximum number of tasks to generate (default: 10)
        - min_tasks: Minimum number of tasks to generate (default: 2)
        - context: Additional context for the AI to consider

    Inputs:
        - goal: High-level exploration goal or question
        - codebase_path: Path to codebase being explored (optional, for context)
        - focus_areas: Optional list of areas to focus on
        - constraints: Optional constraints (e.g., "focus on security", "prioritize performance")

    Returns:
        - tasks: List of AI-generated exploration tasks
        - task_count: Number of tasks created
        - reasoning: AI's reasoning for the split
        - metadata: Split metadata

    Example:
        Input goal: "Understand how the authentication system works"

        AI-generated tasks:
        1. "Explore user login flow and session management"
        2. "Investigate password hashing and credential storage"
        3. "Analyze JWT token generation and validation"
        4. "Find OAuth integration and third-party auth providers"
        5. "Review authentication middleware and route protection"
    """

    def __init__(self, config: Dict[str, Any], inputs: Dict[str, Any]):
        """Initialize AI split operation."""
        super().__init__(config, inputs)
        self.logger = logging.getLogger(__name__)

    def validate(self) -> Optional[str]:
        """Validate AI split configuration."""
        if "goal" not in self.inputs:
            return "AI split operation requires 'goal' input"

        max_tasks = self.config.get("max_tasks", 10)
        min_tasks = self.config.get("min_tasks", 2)

        if max_tasks < min_tasks:
            return f"max_tasks ({max_tasks}) must be >= min_tasks ({min_tasks})"

        return None

    async def execute(self) -> Dict[str, Any]:
        """Execute AI-powered task splitting."""
        goal = self.inputs.get("goal")
        codebase_path = self.inputs.get("codebase_path")
        focus_areas = self.inputs.get("focus_areas", [])
        constraints = self.inputs.get("constraints")

        # Get config
        model = self.config.get("model", "haiku")
        max_tasks = self.config.get("max_tasks", 10)
        min_tasks = self.config.get("min_tasks", 2)
        context = self.config.get("context", "")

        # Build prompt for AI
        prompt = self._build_split_prompt(
            goal=goal,
            codebase_path=codebase_path,
            focus_areas=focus_areas,
            constraints=constraints,
            context=context,
            min_tasks=min_tasks,
            max_tasks=max_tasks
        )

        # Call AI to generate split
        # TODO: Integrate with actual AI executor
        # For now, return a structured placeholder that shows the pattern
        ai_response = await self._call_ai_for_split(prompt, model)

        # Parse AI response into tasks
        tasks = self._parse_ai_response(ai_response, min_tasks, max_tasks)

        return {
            "tasks": tasks,
            "task_count": len(tasks),
            "reasoning": ai_response.get("reasoning", ""),
            "metadata": {
                "goal": goal,
                "model_used": model,
                "min_tasks": min_tasks,
                "max_tasks": max_tasks,
                "ai_reasoning": ai_response.get("reasoning", ""),
            },
        }

    def _build_split_prompt(
        self,
        goal: str,
        codebase_path: Optional[str],
        focus_areas: List[str],
        constraints: Optional[str],
        context: str,
        min_tasks: int,
        max_tasks: int
    ) -> str:
        """
        Build prompt for AI to generate task split.

        Args:
            goal: High-level exploration goal
            codebase_path: Path to codebase
            focus_areas: Areas to focus on
            constraints: Additional constraints
            context: Extra context
            min_tasks: Minimum tasks to generate
            max_tasks: Maximum tasks to generate

        Returns:
            Formatted prompt for AI
        """
        prompt = f"""You are an expert at breaking down complex codebase exploration goals into focused, parallel tasks.

**Goal:** {goal}
"""

        if codebase_path:
            prompt += f"\n**Codebase:** {codebase_path}"

        if focus_areas:
            prompt += f"\n**Focus Areas:** {', '.join(focus_areas)}"

        if constraints:
            prompt += f"\n**Constraints:** {constraints}"

        if context:
            prompt += f"\n**Additional Context:** {context}"

        prompt += f"""

Your task is to break this down into {min_tasks}-{max_tasks} focused exploration sub-tasks that can be executed in parallel.

**Guidelines:**
1. Each task should be specific and actionable
2. Tasks should be independent and non-overlapping
3. Together, tasks should comprehensively cover the goal
4. Consider different aspects: implementation, usage, architecture, flow, edge cases
5. Use clear, specific questions or investigation targets

**Output Format (JSON):**
{{
  "reasoning": "Brief explanation of your split strategy",
  "tasks": [
    {{
      "title": "Short descriptive title",
      "query": "Specific exploration question or target",
      "type": "question|implementation|structure|usage|flow",
      "priority": "high|medium|low",
      "estimated_complexity": "simple|moderate|complex"
    }},
    ...
  ]
}}

Generate the split now:"""

        return prompt

    async def _call_ai_for_split(self, prompt: str, model: str) -> Dict[str, Any]:
        """
        Call AI model to generate task split.

        Args:
            prompt: Prompt for AI
            model: Model to use

        Returns:
            AI response with reasoning and tasks
        """
        from utils.agent import SpecializedAgent, AgentConfig, CLIType
        from utils.agent.cli_executor import CLIExecutor, CLIConfig

        # Create a simple agent config for the split task
        cli_config = CLIConfig(
            cli_type=CLIType.CLAUDE,
            model=model,
            skip_permissions=True
        )

        executor = CLIExecutor(cli_config)

        try:
            # Execute the prompt with the AI
            response = await executor.execute(prompt)

            # Try to parse as JSON
            # The AI should return JSON, but handle cases where it adds explanation
            response_text = response.strip()

            # Find JSON in response (AI might add explanation before/after)
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1

            if json_start >= 0 and json_end > json_start:
                json_text = response_text[json_start:json_end]
                return json.loads(json_text)
            else:
                # If no JSON found, create a fallback response
                self.logger.warning("AI response didn't contain valid JSON, using fallback")
                return self._create_fallback_split(response_text)

        except Exception as e:
            self.logger.error(f"Error calling AI for split: {e}", exc_info=True)
            # Return fallback split on error
            return self._create_fallback_split(str(e))

    def _create_fallback_split(self, error_context: str) -> Dict[str, Any]:
        """
        Create a fallback split when AI call fails.

        Args:
            error_context: Error message or context

        Returns:
            Fallback split response
        """
        goal = self.inputs.get("goal", "unknown goal")

        return {
            "reasoning": f"Fallback split due to error. Creating basic exploration tasks for: {goal}",
            "tasks": [
                {
                    "title": "Overview and Architecture",
                    "query": f"Provide an overview of {goal}",
                    "type": "structure",
                    "priority": "high",
                    "estimated_complexity": "moderate"
                },
                {
                    "title": "Implementation Details",
                    "query": f"Explore the implementation of {goal}",
                    "type": "implementation",
                    "priority": "high",
                    "estimated_complexity": "complex"
                },
                {
                    "title": "Usage and Examples",
                    "query": f"Find how {goal} is used in the codebase",
                    "type": "usage",
                    "priority": "medium",
                    "estimated_complexity": "simple"
                }
            ]
        }

    def _parse_ai_response(
        self,
        ai_response: Dict[str, Any],
        min_tasks: int,
        max_tasks: int
    ) -> List[Dict[str, Any]]:
        """
        Parse and validate AI response.

        Args:
            ai_response: Response from AI
            min_tasks: Minimum tasks required
            max_tasks: Maximum tasks allowed

        Returns:
            List of validated tasks
        """
        tasks = ai_response.get("tasks", [])

        # Validate task count
        if len(tasks) < min_tasks:
            self.logger.warning(
                f"AI generated {len(tasks)} tasks, less than minimum {min_tasks}"
            )
        elif len(tasks) > max_tasks:
            self.logger.warning(
                f"AI generated {len(tasks)} tasks, truncating to {max_tasks}"
            )
            tasks = tasks[:max_tasks]

        # Enrich tasks with index
        for i, task in enumerate(tasks):
            task["index"] = i

        return tasks
