"""Tests for data models."""

import pytest
from utils.async_jobs.models import JobState, JobResult, JobProgress


def test_job_state_enum():
    """Test JobState enum values."""
    assert JobState.QUEUED.value == "queued"
    assert JobState.RUNNING.value == "running"
    assert JobState.COMPLETED.value == "completed"
    assert JobState.FAILED.value == "failed"
    assert JobState.CANCELLED.value == "cancelled"


def test_job_result_creation():
    """Test JobResult creation and defaults."""
    # Test with minimal data
    result = JobResult(success=True)
    assert result.success is True
    assert result.data is None
    assert result.error is None
    assert result.metadata == {}

    # Test with full data
    result = JobResult(
        success=False,
        data="test_data",
        error="test_error",
        metadata={"key": "value"}
    )
    assert result.success is False
    assert result.data == "test_data"
    assert result.error == "test_error"
    assert result.metadata == {"key": "value"}


def test_job_progress_creation():
    """Test JobProgress creation and percentage calculation."""
    # Test basic progress
    progress = JobProgress(current=5, total=10)
    assert progress.current == 5
    assert progress.total == 10
    assert progress.message is None
    assert progress.percentage == 50.0

    # Test with message
    progress = JobProgress(current=3, total=4, message="Processing...")
    assert progress.message == "Processing..."
    assert progress.percentage == 75.0

    # Test edge cases
    progress = JobProgress(current=0, total=0)
    assert progress.percentage == 0.0

    progress = JobProgress(current=10, total=10)
    assert progress.percentage == 100.0
