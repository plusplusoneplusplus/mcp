"""
Decompose Agent

A specialized agent for decomposing complex questions and tasks into parallelizable subtasks.
"""

import logging
from typing import Optional

from utils.agent import SpecializedAgent, AgentConfig

logger = logging.getLogger(__name__)


class DecomposeAgent(SpecializedAgent):
    """
    Specialized agent for task decomposition.

    This agent is designed to:
    - Analyze complex questions and tasks
    - Break them down into focused, independent subtopics
    - Create parallelizable exploration tasks
    - Provide reasoning for decomposition strategy
    """

    def __init__(self, config: AgentConfig):
        """
        Initialize the Decompose Agent.

        Args:
            config: AgentConfig with decomposition-specific settings
        """
        super().__init__(config)

    def get_system_prompt(self) -> str:
        """
        Get the system prompt for the Decompose Agent.

        Returns:
            System prompt that defines the agent's task decomposition behavior
        """
        if self.config.include_session_in_prompt:
            return self.get_default_system_prompt(
                agent_role="You are an expert task planner specialized in decomposing complex questions into parallelizable subtasks.",
                custom_instructions=self._get_decomposition_instructions()
            )

        return """# Task Decomposition Agent

## Role
You are an expert task planner specialized in decomposing complex questions into parallelizable subtasks.

Your role is to analyze questions and break them down into focused, independently explorable subtopics that can be investigated in parallel by different agents.

## Capabilities
You excel at:
1. **Question Analysis**: Understanding the core intent and scope of complex questions
2. **Subtopic Identification**: Breaking questions into logical, independent components
3. **Task Formulation**: Creating clear, actionable exploration tasks for each subtopic
4. **Prioritization**: Ordering subtopics by importance and logical progression
5. **Reasoning**: Explaining decomposition strategy and rationale

## Decomposition Guidelines

### 1. Subtopic Quality
- Each subtopic should be **focused** and **independently explorable**
- Avoid overlapping or redundant subtopics
- Ensure subtopics cover different aspects of the main question
- Make subtopics specific enough to be actionable

### 2. Parallelization
- Design subtopics that can be investigated simultaneously
- Minimize dependencies between subtopics
- Allow different agents to work on different subtopics without conflicts

### 3. Exploration Tasks
- Write clear, focused questions for each subtopic
- Make tasks directly investigable by exploration agents
- Include context about what information to look for
- Specify expected findings to guide exploration

### 4. Count and Balance
- Create an appropriate number of subtopics (typically 2-6)
- Balance breadth (covering all aspects) with depth (keeping focus)
- Consider the complexity of the original question
- Don't over-decompose simple questions

### 5. Importance Levels
- **High**: Critical to answering the main question
- **Medium**: Important but supporting information
- **Low**: Nice to have, provides additional context

## Response Format
Always respond with a JSON object following this structure:
```json
{
  "reasoning": "Brief explanation of decomposition strategy",
  "subtopic_count": <number>,
  "subtopics": [
    {
      "id": "subtopic_1",
      "title": "Brief title",
      "exploration_task": "Specific question for exploration",
      "importance": "high|medium|low",
      "expected_findings": "What this subtopic should reveal"
    }
  ]
}
```

## Quality Criteria
Good decompositions:
- ✓ Cover all aspects of the original question
- ✓ Create independent, parallelizable subtopics
- ✓ Provide clear exploration tasks
- ✓ Balance specificity with scope
- ✓ Order subtopics logically

Poor decompositions:
- ✗ Overlapping or redundant subtopics
- ✗ Subtopics that depend on each other
- ✗ Vague or ambiguous exploration tasks
- ✗ Too many or too few subtopics
- ✗ Random ordering without logic
"""

    def _get_decomposition_instructions(self) -> str:
        """
        Get decomposition-specific instructions for the system prompt.

        Returns:
            Custom instructions for task decomposition
        """
        return """
## Decomposition Guidelines
1. Analyze the question's scope and complexity
2. Identify independent, parallelizable aspects
3. Create focused exploration tasks for each subtopic
4. Assign importance levels (high/medium/low)
5. Order subtopics logically by importance

## Response Format
Always return a JSON object with:
- reasoning: Explanation of your decomposition strategy
- subtopic_count: Number of subtopics created
- subtopics: Array of subtopic objects with id, title, exploration_task, importance, and expected_findings
"""

    async def decompose(
        self,
        question: str,
        min_subtopics: int = 2,
        max_subtopics: int = 6,
    ) -> dict:
        """
        Decompose a question into parallelizable subtopics.

        Args:
            question: The main question or task to decompose
            min_subtopics: Minimum number of subtopics to create
            max_subtopics: Maximum number of subtopics to create

        Returns:
            Dictionary with decomposition results including subtopics and reasoning
        """
        prompt = f"""Analyze the following question and decompose it into specific subtopics that can be explored in parallel.

Question:
{question}

Guidelines:
- Create between {min_subtopics} and {max_subtopics} subtopics
- Each subtopic should be focused and independently explorable
- Subtopics should cover different aspects of the main question
- Avoid overlapping or redundant subtopics
- Order subtopics by importance/logical progression

Respond with a JSON object:
{{
  "reasoning": "Brief explanation of your decomposition strategy and why you chose this number of subtopics",
  "subtopic_count": <number of subtopics>,
  "subtopics": [
    {{
      "id": "subtopic_1",
      "title": "Brief title",
      "exploration_task": "Specific question or task for the exploration agent",
      "importance": "high|medium|low",
      "expected_findings": "What kind of information this subtopic should reveal"
    }},
    ...
  ]
}}

Make each exploration_task a clear, focused question that an agent can directly investigate."""

        return await self.invoke(prompt, include_history=False)

    def __repr__(self) -> str:
        """String representation of the Decompose Agent"""
        return (
            f"DecomposeAgent("
            f"cli_type='{self.config.cli_type.value}', "
            f"model='{self._executor.config.get_default_model()}', "
            f"session_id='{self._get_session_id()}')"
        )
