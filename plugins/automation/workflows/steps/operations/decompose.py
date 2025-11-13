"""Decompose Operation - AI-powered task decomposition."""

import json
import logging
import re
from typing import Any, Dict, Optional, List

from .base import BaseOperation
from utils.agent.agent import SpecializedAgent, AgentConfig
from utils.agent.cli_executor import CLIType


class DecomposeOperation(BaseOperation):
    """
    AI-powered task decomposition.

    Uses the internal agent system to analyze a question or task and decompose it into
    multiple subtopics that can be explored in parallel by agents.

    Inspired by Anthropic's multi-agent research system approach.

    Config:
        - min_subtopics: Minimum number of subtopics (default: 2)
        - max_subtopics: Maximum number of subtopics (default: 6)
        - cli_type: CLI type to use - "claude", "codex", or "copilot" (default: "copilot")
        - model: Optional AI model to use (depends on CLI type)

    Inputs:
        - question: The main question or task to decompose

    Returns:
        - subtopics: List of subtopics with exploration tasks
        - subtopic_count: Number of subtopics created
        - reasoning: AI's reasoning for the decomposition
        - metadata: Additional information about decomposition

    Example:
        config:
          operation: decompose
          min_subtopics: 2
          max_subtopics: 5
          cli_type: copilot
        inputs:
          question: "How does the MCP workflow system work?"
        # Result: 3-5 subtopics like:
        # - "Workflow definition and YAML structure"
        # - "Step execution and dependency resolution"
        # - "Agent integration and tool registry"
    """

    def __init__(self, config: Dict[str, Any], inputs: Dict[str, Any]):
        """Initialize decompose operation."""
        super().__init__(config, inputs)
        self.logger = logging.getLogger(__name__)

    def validate(self) -> Optional[str]:
        """Validate configuration."""
        if "question" not in self.inputs:
            return "decompose operation requires 'question' input"
        return None

    async def execute(self) -> Dict[str, Any]:
        """
        Execute task decomposition using AI.

        Returns:
            Dictionary with subtopics and metadata
        """
        try:
            question = self.inputs.get("question", "")
            min_subtopics = self.config.get("min_subtopics", 2)
            max_subtopics = self.config.get("max_subtopics", 6)
            model = self.config.get("model")
            cli_type = self.config.get("cli_type", "copilot")

            self.logger.info("=" * 60)
            self.logger.info("Starting task decomposition operation")
            self.logger.info(f"Question: {question[:100]}..." if len(question) > 100 else f"Question: {question}")
            self.logger.info(f"Config: cli_type={cli_type}, model={model}, subtopics={min_subtopics}-{max_subtopics}")
            self.logger.info("=" * 60)

            # Create a specialized agent for task decomposition
            self.logger.debug("Creating specialized decompose agent")
            agent_config = AgentConfig(
                cli_type=CLIType(cli_type),
                model=model,
                session_id="decompose_operation",
                skip_permissions=True,
            )

            # Create anonymous agent class inline
            class DecomposeAgent(SpecializedAgent):
                def get_system_prompt(self) -> str:
                    return """You are an expert task planner specialized in decomposing complex questions into parallelizable subtasks.

Your role is to analyze questions and break them down into focused, independently explorable subtopics that can be investigated in parallel by different agents."""

            agent = DecomposeAgent(agent_config)
            self.logger.debug("Agent created successfully")

            # Construct prompt for AI decomposition
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

            self.logger.info(f"Invoking agent for task decomposition (cli_type={cli_type})")
            self.logger.debug(f"Full prompt length: {len(prompt)} characters")

            # Invoke the agent
            response_text = await agent.invoke(prompt, include_history=False)

            self.logger.info(f"Received response from agent ({len(response_text)} characters)")
            self.logger.debug(f"Response preview: {response_text[:200]}...")

            # Extract JSON from response
            if "```json" in response_text:
                self.logger.debug("Extracting JSON from ```json code block")
                json_str = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                self.logger.debug("Extracting JSON from ``` code block")
                json_str = response_text.split("```")[1].split("```")[0].strip()
            else:
                self.logger.debug("Using full response as JSON")
                json_str = response_text.strip()

            # Log the raw JSON for debugging
            self.logger.debug(f"Extracted JSON length: {len(json_str)} characters")
            self.logger.debug(f"JSON preview: {json_str[:200]}...")

            # Parse JSON with strict=False to handle control characters
            self.logger.debug("Attempting to parse JSON response")
            try:
                ai_result = json.loads(json_str, strict=False)
                self.logger.debug("JSON parsed successfully on first attempt")
            except json.JSONDecodeError as e:
                # If that fails, try to clean the string
                self.logger.warning(f"JSON parsing failed on first attempt: {e}")
                self.logger.warning(f"Error at position {e.pos}: '{json_str[max(0, e.pos-20):e.pos+20]}'")

                # More aggressive cleaning: replace actual control characters
                # Remove any actual control characters (ASCII 0-31 except tab/newline in proper contexts)
                cleaned_json = json_str

                # Replace literal newlines and tabs that appear in string values
                # This is a simple approach - just remove them
                cleaned_json = cleaned_json.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')

                self.logger.info("Attempting to parse cleaned JSON")
                # Try parsing the cleaned version
                try:
                    ai_result = json.loads(cleaned_json, strict=False)
                    self.logger.info("JSON parsed successfully after cleaning")
                except json.JSONDecodeError as e2:
                    # Last resort: log the problematic JSON and use fallback
                    self.logger.error(f"Failed to parse JSON even after cleaning: {e2}")
                    self.logger.error(f"Error at position {e2.pos}: '{cleaned_json[max(0, e2.pos-20):e2.pos+20]}'")
                    self.logger.error(f"Problematic JSON (first 500 chars): {json_str[:500]}")
                    self.logger.error(f"Full JSON length: {len(json_str)} characters")
                    raise

            subtopics = ai_result.get("subtopics", [])
            reasoning = ai_result.get("reasoning", "")

            self.logger.info(f"✓ Successfully decomposed into {len(subtopics)} subtopics")
            self.logger.info(f"✓ AI reasoning: {reasoning[:100]}..." if len(reasoning) > 100 else f"✓ AI reasoning: {reasoning}")

            # Log each subtopic
            for i, subtopic in enumerate(subtopics, 1):
                title = subtopic.get("title", "")
                importance = subtopic.get("importance", "")
                self.logger.debug(f"  Subtopic {i}: {title} [{importance}]")

            # Transform subtopics into exploration tasks
            self.logger.debug("Transforming subtopics into exploration tasks")
            exploration_tasks = []
            for subtopic in subtopics:
                exploration_tasks.append({
                    "subtopic_id": subtopic.get("id", f"subtopic_{len(exploration_tasks)}"),
                    "title": subtopic.get("title", ""),
                    "exploration_task": subtopic.get("exploration_task", ""),
                    "importance": subtopic.get("importance", "medium"),
                    "expected_findings": subtopic.get("expected_findings", ""),
                })

            result = {
                "subtopics": exploration_tasks,
                "subtopic_count": len(exploration_tasks),
                "reasoning": reasoning,
                "metadata": {
                    "original_question": question,
                    "cli_type": cli_type,
                    "model": model,
                    "ai_decomposition": True,
                },
            }

            self.logger.info("=" * 60)
            self.logger.info(f"✓ Decomposition complete: {len(exploration_tasks)} tasks created")
            self.logger.info("=" * 60)

            return result

        except Exception as e:
            self.logger.error("=" * 60)
            self.logger.error(f"✗ Task decomposition failed: {e}", exc_info=True)
            self.logger.error("=" * 60)
            # Fallback: create single basic exploration task
            self.logger.warning("Using fallback: creating single exploration task")
            fallback_result = {
                "subtopics": [{
                    "subtopic_id": "fallback",
                    "title": "General Exploration",
                    "exploration_task": self.inputs.get("question", ""),
                    "importance": "high",
                    "expected_findings": "General information about the topic",
                }],
                "subtopic_count": 1,
                "reasoning": f"Fallback due to error: {str(e)}",
                "metadata": {
                    "original_question": self.inputs.get("question", ""),
                    "ai_decomposition": False,
                    "fallback": True,
                },
            }

            self.logger.info("Fallback decomposition created with 1 task")
            return fallback_result
