"""Tests for map-reduce exploration operations."""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

from plugins.automation.workflows.steps.operations import (
    SplitOperation,
    ExplorationOperation,
    SummarizeOperation,
)


class TestSplitOperation:
    """Test split operation for map-reduce workflows."""

    def test_split_by_items(self):
        """Test splitting one task per item."""
        config = {"operation": "split", "strategy": "by_items"}
        inputs = {"items": ["task1", "task2", "task3", "task4"]}

        operation = SplitOperation(config, inputs)
        assert operation.validate() is None

    @pytest.mark.asyncio
    async def test_split_by_items_execution(self):
        """Test split by items execution."""
        config = {"strategy": "by_items"}
        inputs = {"items": ["Q1", "Q2", "Q3"]}

        operation = SplitOperation(config, inputs)
        result = await operation.execute()

        assert result["task_count"] == 3
        assert len(result["tasks"]) == 3
        assert result["tasks"][0]["item"] == "Q1"
        assert result["tasks"][1]["index"] == 1
        assert result["metadata"]["strategy"] == "by_items"

    @pytest.mark.asyncio
    async def test_split_by_count(self):
        """Test splitting into N chunks."""
        config = {"strategy": "by_count", "count": 2}
        inputs = {"items": [1, 2, 3, 4, 5, 6]}

        operation = SplitOperation(config, inputs)
        result = await operation.execute()

        assert result["task_count"] <= 2
        # Should have roughly equal distribution
        total_items = sum(len(task["items"]) for task in result["tasks"])
        assert total_items == 6

    @pytest.mark.asyncio
    async def test_split_by_chunk_size(self):
        """Test splitting by chunk size."""
        config = {"strategy": "by_chunk_size", "chunk_size": 2}
        inputs = {"items": [1, 2, 3, 4, 5]}

        operation = SplitOperation(config, inputs)
        result = await operation.execute()

        assert result["task_count"] == 3  # 2 + 2 + 1
        assert len(result["tasks"][0]["items"]) == 2
        assert len(result["tasks"][1]["items"]) == 2
        assert len(result["tasks"][2]["items"]) == 1

    def test_split_validation_errors(self):
        """Test split operation validation."""
        # Invalid strategy
        op = SplitOperation({"strategy": "invalid"}, {})
        assert "Invalid strategy" in op.validate()

        # Missing count for by_count
        op = SplitOperation({"strategy": "by_count"}, {})
        assert "requires 'count'" in op.validate()

        # Missing chunk_size for by_chunk_size
        op = SplitOperation({"strategy": "by_chunk_size"}, {})
        assert "requires 'chunk_size'" in op.validate()

    @pytest.mark.asyncio
    async def test_split_with_single_item(self):
        """Test split with single non-list item."""
        config = {"strategy": "by_items"}
        inputs = {"data": "single_task"}  # Not in 'items' key

        operation = SplitOperation(config, inputs)
        result = await operation.execute()

        assert result["task_count"] == 1
        assert result["tasks"][0]["item"] == "single_task"


class TestExplorationOperation:
    """Test exploration operation for AI-powered exploration."""

    def test_exploration_validation(self):
        """Test exploration operation validation."""
        # Valid exploration type
        op = ExplorationOperation({"exploration_type": "question"}, {})
        assert op.validate() is None

        # Invalid exploration type
        op = ExplorationOperation({"exploration_type": "invalid"}, {})
        assert "Invalid exploration_type" in op.validate()

    @pytest.mark.asyncio
    async def test_exploration_execution(self):
        """Test basic exploration execution."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {
                "exploration_type": "question",
                "session_dir": tmpdir,
                "save_to_session": True,
            }
            inputs = {
                "task": {"item": "How does auth work?", "index": 0},
                "codebase_path": "/fake/path",
                "question": "How does auth work?"
            }

            operation = ExplorationOperation(config, inputs)

            # Mock ExploreAgent to avoid real AI calls
            with patch('plugins.automation.agents.ExploreAgent') as MockAgent:
                mock_agent = MockAgent.return_value
                mock_agent.explore = AsyncMock(return_value="Authentication uses JWT tokens...")

                result = await operation.execute()

                assert "finding" in result
                assert result["finding"]["exploration_type"] == "question"
                assert result["finding"]["status"] == "completed"
                assert "JWT tokens" in result["finding"]["result"]
                assert result["task_info"]["index"] == 0
                assert result["metadata"]["saved_to_session"] is True

    @pytest.mark.asyncio
    async def test_exploration_session_storage(self):
        """Test that exploration findings are stored in session files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {
                "exploration_type": "question",
                "session_dir": tmpdir,
                "session_id": "test_session",
                "save_to_session": True,
            }
            inputs = {
                "task": {"item": "Test question", "index": 5},
                "question": "Test question",
            }

            operation = ExplorationOperation(config, inputs)

            # Mock ExploreAgent
            with patch('plugins.automation.agents.ExploreAgent') as MockAgent:
                mock_agent = MockAgent.return_value
                mock_agent.explore = AsyncMock(return_value="Test result")

                result = await operation.execute()

                # Check session file was created
                session_file = Path(result["session_file"])
                assert session_file.exists()

                # Verify content
                with open(session_file) as f:
                    data = json.load(f)
                    assert data["session_id"] == "test_session"
                    assert data["task_index"] == 5
                    assert data["exploration_type"] == "question"
                    assert "finding" in data
                    assert data["finding"]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_exploration_without_session_storage(self):
        """Test exploration without saving to session."""
        config = {"exploration_type": "question", "save_to_session": False}
        inputs = {"task": "Simple task", "question": "Simple question"}

        operation = ExplorationOperation(config, inputs)

        # Mock ExploreAgent
        with patch('plugins.automation.agents.ExploreAgent') as MockAgent:
            mock_agent = MockAgent.return_value
            mock_agent.explore = AsyncMock(return_value="Result")

            result = await operation.execute()

            assert result["session_file"] is None
            assert result["metadata"]["saved_to_session"] is False
            assert result["finding"]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_exploration_types(self):
        """Test different exploration types call appropriate agent methods."""
        test_cases = [
            ("question", "explore", "What is this?"),
            ("implementation", "find_implementation", "auth_function"),
            ("structure", "analyze_structure", "auth_module"),
            ("usage", "find_usage", "User"),
            ("flow", "explain_flow", "login process"),
        ]

        for exp_type, method_name, query in test_cases:
            config = {"exploration_type": exp_type, "save_to_session": False}
            inputs = {
                "task": {"item": query, "index": 0},
                "codebase_path": "/code"
            }

            # Add type-specific input
            if exp_type == "question":
                inputs["question"] = query
            elif exp_type == "implementation":
                inputs["feature"] = query
            elif exp_type == "structure":
                inputs["component"] = query
            elif exp_type == "usage":
                inputs["symbol"] = query
            elif exp_type == "flow":
                inputs["flow"] = query

            operation = ExplorationOperation(config, inputs)

            with patch('plugins.automation.agents.ExploreAgent') as MockAgent:
                mock_agent = MockAgent.return_value
                mock_method = AsyncMock(return_value=f"Result for {query}")
                setattr(mock_agent, method_name, mock_method)

                result = await operation.execute()

                # Verify correct method was called
                assert mock_method.called, f"Method {method_name} should have been called for {exp_type}"
                assert result["finding"]["status"] == "completed"
                assert query in result["finding"]["result"]

    @pytest.mark.asyncio
    async def test_exploration_error_handling(self):
        """Test exploration handles agent errors gracefully."""
        config = {"exploration_type": "question", "save_to_session": False}
        inputs = {"task": "Test", "question": "Test question"}

        operation = ExplorationOperation(config, inputs)

        # Mock ExploreAgent to raise exception
        with patch('plugins.automation.agents.ExploreAgent') as MockAgent:
            mock_agent = MockAgent.return_value
            mock_agent.explore = AsyncMock(side_effect=Exception("API error"))

            result = await operation.execute()

            # Should return failed status, not raise exception
            assert result["finding"]["status"] == "failed"
            assert "error" in result["finding"]
            assert "API error" in result["finding"]["error"]


class TestSummarizeOperation:
    """Test summarize operation for aggregating findings."""

    def test_summarize_validation(self):
        """Test summarize operation validation."""
        # Valid format
        op = SummarizeOperation({"summary_format": "detailed"}, {})
        assert op.validate() is None

        # Invalid format
        op = SummarizeOperation({"summary_format": "invalid"}, {})
        assert "Invalid summary_format" in op.validate()

    @pytest.mark.asyncio
    async def test_summarize_from_findings(self):
        """Test summarizing from finding objects."""
        config = {"summary_format": "detailed", "include_metadata": True}
        findings = [
            {
                "task": "Question 1",
                "exploration_type": "question",
                "finding": {"query": "Q1", "result": "Answer 1"},
                "task_index": 0,
            },
            {
                "task": "Question 2",
                "exploration_type": "question",
                "finding": {"query": "Q2", "result": "Answer 2"},
                "task_index": 1,
            },
        ]
        inputs = {"findings": findings}

        operation = SummarizeOperation(config, inputs)
        result = await operation.execute()

        assert result["finding_count"] == 2
        assert result["summary"]["total_findings"] == 2
        assert len(result["summary"]["findings"]) == 2

    @pytest.mark.asyncio
    async def test_summarize_from_session_files(self):
        """Test summarizing from session files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            session_id = "test_session_123"

            # Create mock session files
            for i in range(3):
                session_file = Path(tmpdir) / f"{session_id}_task_{i}.json"
                data = {
                    "session_id": session_id,
                    "task_index": i,
                    "task": f"Task {i}",
                    "exploration_type": "question",
                    "finding": {"query": f"Q{i}", "result": f"A{i}"},
                }
                with open(session_file, "w") as f:
                    json.dump(data, f)

            config = {
                "summary_format": "structured",
                "session_dir": tmpdir,
                "session_id": session_id,
            }
            inputs = {"session_id": session_id}

            operation = SummarizeOperation(config, inputs)
            result = await operation.execute()

            assert result["finding_count"] == 3
            assert len(result["session_files_read"]) == 3
            assert result["summary"]["total_findings"] == 3

    @pytest.mark.asyncio
    async def test_summarize_concise_format(self):
        """Test concise summary format."""
        config = {"summary_format": "concise", "include_metadata": True}
        findings = [
            {
                "exploration_type": "question",
                "finding": {
                    "query": "Test query",
                    "result": "Long result " * 20,
                    "status": "completed",
                },
            }
        ]
        inputs = {"findings": findings}

        operation = SummarizeOperation(config, inputs)
        result = await operation.execute()

        summary = result["summary"]
        assert "key_findings" in summary
        assert summary["total_findings"] == 1
        # Result should be truncated to 100 chars
        assert len(summary["key_findings"][0]["result_preview"]) <= 100

    @pytest.mark.asyncio
    async def test_summarize_structured_format(self):
        """Test structured summary format grouped by type."""
        config = {"summary_format": "structured"}
        findings = [
            {"exploration_type": "question", "task": "Q1", "finding": {"result": "A1"}},
            {"exploration_type": "question", "task": "Q2", "finding": {"result": "A2"}},
            {
                "exploration_type": "implementation",
                "task": "F1",
                "finding": {"result": "impl"},
            },
        ]
        inputs = {"findings": findings}

        operation = SummarizeOperation(config, inputs)
        result = await operation.execute()

        summary = result["summary"]
        assert "by_exploration_type" in summary
        assert summary["by_exploration_type"]["question"]["count"] == 2
        assert summary["by_exploration_type"]["implementation"]["count"] == 1

    @pytest.mark.asyncio
    async def test_summarize_output_file(self):
        """Test writing summary to output file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "summary.json"

            config = {"summary_format": "detailed", "output_file": str(output_file)}
            findings = [{"task": "Task 1", "finding": {"result": "Result 1"}}]
            inputs = {"findings": findings}

            operation = SummarizeOperation(config, inputs)
            await operation.execute()

            # Verify file was created
            assert output_file.exists()

            # Verify content
            with open(output_file) as f:
                data = json.load(f)
                assert data["total_findings"] == 1

    @pytest.mark.asyncio
    async def test_summarize_empty_findings(self):
        """Test summarizing with no findings."""
        config = {"summary_format": "detailed"}
        inputs = {"findings": []}

        operation = SummarizeOperation(config, inputs)
        result = await operation.execute()

        assert result["finding_count"] == 0
        assert "No findings" in result["summary"]["message"]


class TestMapReduceIntegration:
    """Integration tests for full map-reduce workflow."""

    @pytest.mark.asyncio
    async def test_full_mapreduce_flow(self):
        """Test complete split -> explore -> summarize flow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            session_id = "integration_test"

            # Step 1: Split
            split_config = {"strategy": "by_items"}
            split_inputs = {"items": ["Q1", "Q2", "Q3"]}
            split_op = SplitOperation(split_config, split_inputs)
            split_result = await split_op.execute()

            assert split_result["task_count"] == 3

            # Step 2: Explore (simulate parallel execution)
            # Mock ExploreAgent for all explorations
            with patch('plugins.automation.agents.ExploreAgent') as MockAgent:
                mock_agent = MockAgent.return_value
                mock_agent.explore = AsyncMock(side_effect=[
                    "Answer to Q1",
                    "Answer to Q2",
                    "Answer to Q3"
                ])

                exploration_results = []
                for task in split_result["tasks"]:
                    explore_config = {
                        "exploration_type": "question",
                        "session_dir": tmpdir,
                        "session_id": session_id,
                        "save_to_session": True,
                    }
                    explore_inputs = {"task": task, "question": task["item"]}
                    explore_op = ExplorationOperation(explore_config, explore_inputs)
                    explore_result = await explore_op.execute()
                    exploration_results.append(explore_result)

                assert len(exploration_results) == 3

                # Verify all explorations completed
                for result in exploration_results:
                    assert result["finding"]["status"] == "completed"

            # Step 3: Summarize
            summarize_config = {
                "summary_format": "structured",
                "session_dir": tmpdir,
                "session_id": session_id,
            }
            summarize_inputs = {"session_id": session_id}
            summarize_op = SummarizeOperation(summarize_config, summarize_inputs)
            summarize_result = await summarize_op.execute()

            # Verify final result
            assert summarize_result["finding_count"] == 3
            assert len(summarize_result["session_files_read"]) == 3
            assert summarize_result["summary"]["total_findings"] == 3
