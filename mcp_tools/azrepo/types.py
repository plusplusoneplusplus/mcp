from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field
from datetime import datetime


class PullRequestIdentity(BaseModel):
    """Azure DevOps identity information"""

    display_name: str
    id: str
    unique_name: Optional[str] = None
    image_url: Optional[str] = None


class PullRequestWorkItem(BaseModel):
    """Work item linked to a pull request"""

    id: str
    url: str
    title: Optional[str] = None
    state: Optional[str] = None
    type: Optional[str] = None


class PullRequestRef(BaseModel):
    """Git reference information"""

    name: str
    repository: Dict[str, Any]
    source_reference_name: Optional[str] = None
    target_reference_name: Optional[str] = None


class PullRequest(BaseModel):
    """Pull request information"""

    pull_request_id: int
    title: str
    status: str
    created_by: PullRequestIdentity
    creation_date: datetime
    source_ref_name: str
    target_ref_name: str
    source_branch: Optional[str] = None
    target_branch: Optional[str] = None
    merge_status: Optional[str] = None
    is_draft: Optional[bool] = False
    description: Optional[str] = None
    reviewers: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    work_items: Optional[List[PullRequestWorkItem]] = Field(default_factory=list)
    repository: Optional[Dict[str, Any]] = None
    url: Optional[str] = None
    completion_options: Optional[Dict[str, Any]] = None
    labels: Optional[List[Dict[str, Any]]] = Field(default_factory=list)


class PullRequestListResponse(BaseModel):
    """Response from list pull requests operation"""

    success: bool
    data: Optional[List[PullRequest]] = None
    error: Optional[str] = None
    raw_output: Optional[str] = None


class PullRequestDetailResponse(BaseModel):
    """Response from get pull request operation"""

    success: bool
    data: Optional[PullRequest] = None
    error: Optional[str] = None
    raw_output: Optional[str] = None


class PullRequestCreateResponse(BaseModel):
    """Response from create pull request operation"""

    success: bool
    data: Optional[PullRequest] = None
    error: Optional[str] = None
    raw_output: Optional[str] = None


class PullRequestUpdateResponse(BaseModel):
    """Response from update pull request operation"""

    success: bool
    data: Optional[PullRequest] = None
    error: Optional[str] = None
    raw_output: Optional[str] = None


class PullRequestVoteEnum(str):
    """Pull request vote values"""

    APPROVE = "approve"
    APPROVE_WITH_SUGGESTIONS = "approve-with-suggestions"
    RESET = "reset"
    REJECT = "reject"
    WAIT_FOR_AUTHOR = "wait-for-author"
