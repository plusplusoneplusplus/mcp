"""Summarization operation for aggregating and summarizing exploration findings."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional, List
from datetime import datetime

from .base import BaseOperation


class SummarizeOperation(BaseOperation):
    """
    Summarize and aggregate exploration findings from session files.

    This operation reads findings from session files (created by exploration operations)
    and creates a comprehensive summary. Designed for the reduce phase of map-reduce
    exploration workflows.

    Config:
        - session_dir: Directory containing session files (default: .mcp_sessions)
        - session_id: Session ID to summarize (optional, will use from inputs if not set)
        - summary_format: Output format (detailed, concise, structured)
        - include_metadata: Include metadata in summary (default: true)
        - output_file: Optional file to write summary to

    Inputs:
        - findings: List of finding objects from exploration steps
        - session_files: List of session file paths to read
        - session_id: Optional session ID to read findings from

    Returns:
        - summary: Aggregated summary of all findings
        - finding_count: Number of findings summarized
        - metadata: Summary metadata
        - session_files_read: List of session files that were read

    Example:
        # Summarize from finding objects
        config:
          operation: summarize
          summary_format: detailed
        inputs:
          findings: [{{ steps.explore_1.result }}, {{ steps.explore_2.result }}]

        # Summarize from session files
        config:
          operation: summarize
          session_dir: .mcp_sessions
          session_id: exploration_20240101_120000
        inputs:
          session_id: exploration_20240101_120000
    """

    def __init__(self, config: Dict[str, Any], inputs: Dict[str, Any]):
        """Initialize summarize operation."""
        super().__init__(config, inputs)
        self.logger = logging.getLogger(__name__)

    def validate(self) -> Optional[str]:
        """Validate summarization configuration."""
        summary_format = self.config.get("summary_format", "detailed")

        valid_formats = ["detailed", "concise", "structured"]
        if summary_format not in valid_formats:
            return f"Invalid summary_format '{summary_format}'. Valid: {', '.join(valid_formats)}"

        return None

    async def execute(self) -> Dict[str, Any]:
        """Execute summarization."""
        session_dir = self.config.get("session_dir", ".mcp_sessions")
        session_id = self.config.get("session_id") or self.inputs.get("session_id")
        summary_format = self.config.get("summary_format", "detailed")
        include_metadata = self.config.get("include_metadata", True)
        output_file = self.config.get("output_file")

        # Collect findings from various sources
        findings = []
        session_files_read = []

        # 1. From direct findings input
        if "findings" in self.inputs:
            findings_input = self.inputs["findings"]
            if isinstance(findings_input, list):
                findings.extend(findings_input)
            else:
                findings.append(findings_input)

        # 2. From session files input
        if "session_files" in self.inputs:
            session_files = self.inputs["session_files"]
            if isinstance(session_files, str):
                session_files = [session_files]
            for file_path in session_files:
                finding = self._read_session_file(file_path)
                if finding:
                    findings.append(finding)
                    session_files_read.append(file_path)

        # 3. From session directory (if session_id provided)
        if session_id and not findings:
            session_path = Path(session_dir)
            if session_path.exists():
                pattern = f"{session_id}_task_*.json"
                for file_path in session_path.glob(pattern):
                    finding = self._read_session_file(str(file_path))
                    if finding:
                        findings.append(finding)
                        session_files_read.append(str(file_path))

        # Generate summary
        summary = self._create_summary(
            findings=findings,
            summary_format=summary_format,
            include_metadata=include_metadata
        )

        # Write to output file if specified
        if output_file:
            self._write_summary_file(summary, output_file)

        return {
            "summary": summary,
            "finding_count": len(findings),
            "session_files_read": session_files_read,
            "metadata": {
                "session_id": session_id,
                "timestamp": datetime.utcnow().isoformat(),
                "summary_format": summary_format,
            },
        }

    def _read_session_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Read finding from session file.

        Args:
            file_path: Path to session file

        Returns:
            Finding dictionary or None if error
        """
        try:
            with open(file_path, "r") as f:
                data = json.load(f)
                return data
        except Exception as e:
            self.logger.error(f"Error reading session file {file_path}: {e}")
            return None

    def _create_summary(
        self,
        findings: List[Dict[str, Any]],
        summary_format: str,
        include_metadata: bool
    ) -> Dict[str, Any]:
        """
        Create summary from findings.

        Args:
            findings: List of findings
            summary_format: Output format
            include_metadata: Include metadata

        Returns:
            Summary dictionary
        """
        if not findings:
            return {
                "message": "No findings to summarize",
                "findings": []
            }

        if summary_format == "concise":
            return self._create_concise_summary(findings, include_metadata)
        elif summary_format == "structured":
            return self._create_structured_summary(findings, include_metadata)
        else:  # detailed
            return self._create_detailed_summary(findings, include_metadata)

    def _create_detailed_summary(
        self,
        findings: List[Dict[str, Any]],
        include_metadata: bool
    ) -> Dict[str, Any]:
        """
        Create detailed summary with all information.

        Args:
            findings: List of findings
            include_metadata: Include metadata

        Returns:
            Detailed summary
        """
        summary = {
            "total_findings": len(findings),
            "findings": [],
        }

        for i, finding in enumerate(findings):
            finding_summary = {
                "index": i,
                "task": finding.get("task"),
                "exploration_type": finding.get("exploration_type"),
                "finding": finding.get("finding"),
            }

            if include_metadata:
                finding_summary["metadata"] = {
                    "task_index": finding.get("task_index"),
                    "timestamp": finding.get("timestamp"),
                    "session_id": finding.get("session_id"),
                }

            summary["findings"].append(finding_summary)

        return summary

    def _create_concise_summary(
        self,
        findings: List[Dict[str, Any]],
        include_metadata: bool
    ) -> Dict[str, Any]:
        """
        Create concise summary with key points only.

        Args:
            findings: List of findings
            include_metadata: Include metadata

        Returns:
            Concise summary
        """
        # Extract key findings
        key_findings = []
        for finding in findings:
            finding_data = finding.get("finding", {})
            if isinstance(finding_data, dict):
                query = finding_data.get("query", "")
                result = finding_data.get("result", "")
                status = finding_data.get("status", "unknown")

                key_findings.append({
                    "query": query,
                    "status": status,
                    "result_preview": str(result)[:100] if result else "N/A"
                })

        summary = {
            "total_findings": len(findings),
            "key_findings": key_findings,
        }

        if include_metadata:
            # Add high-level metadata
            exploration_types = set()
            for f in findings:
                exp_type = f.get("exploration_type")
                if exp_type:
                    exploration_types.add(exp_type)

            summary["metadata"] = {
                "exploration_types": list(exploration_types),
                "first_timestamp": findings[0].get("timestamp") if findings else None,
                "last_timestamp": findings[-1].get("timestamp") if findings else None,
            }

        return summary

    def _create_structured_summary(
        self,
        findings: List[Dict[str, Any]],
        include_metadata: bool
    ) -> Dict[str, Any]:
        """
        Create structured summary grouped by exploration type.

        Args:
            findings: List of findings
            include_metadata: Include metadata

        Returns:
            Structured summary
        """
        # Group by exploration type
        grouped = {}
        for finding in findings:
            exp_type = finding.get("exploration_type", "unknown")
            if exp_type not in grouped:
                grouped[exp_type] = []
            grouped[exp_type].append(finding)

        summary = {
            "total_findings": len(findings),
            "by_exploration_type": {},
        }

        for exp_type, type_findings in grouped.items():
            summary["by_exploration_type"][exp_type] = {
                "count": len(type_findings),
                "findings": [
                    {
                        "task": f.get("task"),
                        "finding": f.get("finding"),
                    }
                    for f in type_findings
                ]
            }

        if include_metadata:
            summary["metadata"] = {
                "exploration_types": list(grouped.keys()),
                "counts_by_type": {
                    exp_type: len(findings)
                    for exp_type, findings in grouped.items()
                },
            }

        return summary

    def _write_summary_file(self, summary: Dict[str, Any], output_file: str):
        """
        Write summary to file.

        Args:
            summary: Summary dictionary
            output_file: Output file path
        """
        try:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, "w") as f:
                json.dump(summary, f, indent=2, default=str)

            self.logger.info(f"Wrote summary to {output_file}")
        except Exception as e:
            self.logger.error(f"Error writing summary file: {e}")
