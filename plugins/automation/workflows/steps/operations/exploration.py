"""Exploration operation for AI-powered codebase exploration with session storage."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional
from datetime import datetime

from .base import BaseOperation
from utils.session.session_manager import SessionManager
from utils.session.storage import SessionStorage


class ExplorationOperation(BaseOperation):
    """
    AI-powered exploration operation with session storage.

    This operation performs AI exploration tasks and stores findings in session files
    for later aggregation. Designed to work in map-reduce workflows where multiple
    explorations run in parallel and results are aggregated.

    Config:
        - exploration_type: Type of exploration (question, implementation, structure, usage, flow)
        - session_dir: Directory to store session files (default: .mcp_sessions)
        - save_to_session: Whether to save findings to session (default: true)
        - session_id: Optional session ID to use

    Inputs:
        - task: Task object from split operation (should contain item, question, or exploration details)
        - question: Optional question to explore (for question exploration)
        - feature: Optional feature to find (for implementation exploration)
        - component: Optional component to analyze (for structure exploration)
        - symbol: Optional symbol to find usage (for usage exploration)
        - flow: Optional flow description (for flow exploration)
        - codebase_path: Path to codebase to explore

    Returns:
        - finding: Exploration result
        - session_file: Path to session file with findings
        - task_info: Information about the task that was explored
        - metadata: Exploration metadata

    Example:
        # Single exploration
        config:
          operation: explore
          exploration_type: question
          session_dir: .mcp_sessions
        inputs:
          task:
            item: "How does authentication work?"
            index: 0
          codebase_path: /path/to/repo

        # Result stored in session file and returned
    """

    def __init__(self, config: Dict[str, Any], inputs: Dict[str, Any]):
        """Initialize exploration operation."""
        super().__init__(config, inputs)
        self.logger = logging.getLogger(__name__)

    def validate(self) -> Optional[str]:
        """Validate exploration configuration."""
        exploration_type = self.config.get("exploration_type", "question")

        # Skip validation for template variables (they'll be resolved at runtime)
        if isinstance(exploration_type, str) and "{{" in exploration_type:
            return None

        valid_types = ["question", "implementation", "structure", "usage", "flow", "generic"]
        if exploration_type not in valid_types:
            return f"Invalid exploration_type '{exploration_type}'. Valid: {', '.join(valid_types)}"

        return None

    async def execute(self) -> Dict[str, Any]:
        """Execute AI exploration and store findings."""
        exploration_type = self.config.get("exploration_type", "question")
        session_dir = self.config.get("session_dir", ".mcp_sessions")
        save_to_session = self.config.get("save_to_session", True)
        session_id = self.config.get("session_id")

        # Extract task information
        task = self.inputs.get("task", {})
        task_item = task.get("item") if isinstance(task, dict) else task
        task_index = task.get("index", 0) if isinstance(task, dict) else 0

        # Get exploration parameters
        codebase_path = self.inputs.get("codebase_path")
        question = self.inputs.get("question") or (task_item if isinstance(task_item, str) else None)
        feature = self.inputs.get("feature") or (task.get("feature") if isinstance(task, dict) else None)
        component = self.inputs.get("component") or (task.get("component") if isinstance(task, dict) else None)
        symbol = self.inputs.get("symbol") or (task.get("symbol") if isinstance(task, dict) else None)
        flow = self.inputs.get("flow") or (task.get("flow") if isinstance(task, dict) else None)

        # Perform exploration (simplified - you can integrate with actual ExploreAgent here)
        finding = await self._perform_exploration(
            exploration_type=exploration_type,
            question=question,
            feature=feature,
            component=component,
            symbol=symbol,
            flow=flow,
            codebase_path=codebase_path,
            task=task
        )

        # Store finding in session if enabled
        session_file = None
        if save_to_session:
            session_file = await self._store_in_session(
                finding=finding,
                task=task,
                task_index=task_index,
                exploration_type=exploration_type,
                session_dir=session_dir,
                session_id=session_id
            )

        return {
            "finding": finding,
            "session_file": session_file,
            "task_info": {
                "index": task_index,
                "task": task_item,
                "exploration_type": exploration_type,
            },
            "metadata": {
                "timestamp": datetime.utcnow().isoformat(),
                "codebase_path": codebase_path,
                "saved_to_session": save_to_session,
            },
        }

    async def _perform_exploration(
        self,
        exploration_type: str,
        question: Optional[str],
        feature: Optional[str],
        component: Optional[str],
        symbol: Optional[str],
        flow: Optional[str],
        codebase_path: Optional[str],
        task: Any
    ) -> Dict[str, Any]:
        """
        Perform the actual AI exploration using ExploreAgent.

        Args:
            exploration_type: Type of exploration
            question: Question to explore
            feature: Feature to find
            component: Component to analyze
            symbol: Symbol to find usage
            flow: Flow to explain
            codebase_path: Codebase path
            task: Task object

        Returns:
            Finding dictionary
        """
        # Import ExploreAgent
        from plugins.automation.agents import ExploreAgent, ExploreAgentConfig
        from utils.agent import CLIType

        # Create agent configuration
        config = ExploreAgentConfig(
            cli_type=CLIType.CLAUDE,
            model=self.config.get("model"),  # Optional model override
            cwd=codebase_path,
            session_id=self.config.get("session_id"),
            working_directories=self.config.get("working_directories")
        )

        # Create agent instance
        agent = ExploreAgent(config)

        # Initialize finding
        finding = {
            "exploration_type": exploration_type,
            "status": "pending",
            "query": question or feature or component or symbol or flow or str(task),
            "result": None,
        }

        try:
            # Execute appropriate exploration based on type
            if exploration_type == "question" and question:
                result = await agent.explore(
                    question=question,
                    codebase_path=codebase_path
                )
            elif exploration_type == "implementation" and feature:
                result = await agent.find_implementation(
                    feature_or_function=feature,
                    codebase_path=codebase_path
                )
            elif exploration_type == "structure" and component:
                result = await agent.analyze_structure(
                    component_or_module=component,
                    codebase_path=codebase_path
                )
            elif exploration_type == "usage" and symbol:
                result = await agent.find_usage(
                    symbol=symbol,
                    codebase_path=codebase_path
                )
            elif exploration_type == "flow" and flow:
                result = await agent.explain_flow(
                    flow_description=flow,
                    codebase_path=codebase_path
                )
            else:
                # Generic exploration if type doesn't match or no specific param
                query = question or feature or component or symbol or flow or str(task)
                result = await agent.explore(
                    question=query,
                    codebase_path=codebase_path
                )

            finding["result"] = result
            finding["status"] = "completed"

        except Exception as e:
            self.logger.error(f"Exploration failed: {e}", exc_info=True)
            finding["status"] = "failed"
            finding["error"] = str(e)

        return finding

    async def _store_in_session(
        self,
        finding: Dict[str, Any],
        task: Any,
        task_index: int,
        exploration_type: str,
        session_dir: str,
        session_id: Optional[str] = None
    ) -> str:
        """
        Store finding in session file.

        Args:
            finding: Exploration finding
            task: Task that was explored
            task_index: Index of the task
            exploration_type: Type of exploration
            session_dir: Directory to store sessions
            session_id: Optional session ID

        Returns:
            Path to session file
        """
        # Create session directory
        session_path = Path(session_dir)
        session_path.mkdir(parents=True, exist_ok=True)

        # Generate session ID if not provided
        if not session_id:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            session_id = f"exploration_{timestamp}"

        # Create finding file for this task
        finding_file = session_path / f"{session_id}_task_{task_index}.json"

        # Prepare finding data
        finding_data = {
            "session_id": session_id,
            "task_index": task_index,
            "task": task,
            "exploration_type": exploration_type,
            "finding": finding,
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Write to file
        with open(finding_file, "w") as f:
            json.dump(finding_data, f, indent=2, default=str)

        self.logger.info(f"Stored finding in {finding_file}")

        return str(finding_file)
