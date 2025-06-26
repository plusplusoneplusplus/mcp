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


class PullRequestComment(BaseModel):
    """Pull request comment information"""

    id: int
    content: str
    author: PullRequestIdentity
    publishedDate: datetime
    commentType: str = "text"  # text, system, codeChange
    parentCommentId: Optional[int] = None
    lastUpdatedDate: Optional[datetime] = None
    lastContentUpdatedDate: Optional[datetime] = None
    isDeleted: Optional[bool] = None
    usersLiked: Optional[List[PullRequestIdentity]] = Field(default_factory=list)

    # Legacy field mappings for backward compatibility
    @property
    def created_date(self) -> datetime:
        return self.publishedDate

    @property
    def parent_comment_id(self) -> Optional[int]:
        return self.parentCommentId

    @property
    def last_updated_date(self) -> Optional[datetime]:
        return self.lastUpdatedDate

    @property
    def comment_type(self) -> str:
        return self.commentType


class PullRequestThread(BaseModel):
    """Pull request comment thread information"""

    id: int
    status: str  # active, closed, fixed, wontFix, etc.
    comments: List[PullRequestComment]
    publishedDate: Optional[datetime] = None
    lastUpdatedDate: Optional[datetime] = None
    properties: Optional[Dict[str, Any]] = Field(default_factory=dict)
    threadContext: Optional[Dict[str, Any]] = None
    pullRequestThreadContext: Optional[Dict[str, Any]] = None
    isDeleted: Optional[bool] = None

    # Legacy field mappings for backward compatibility
    @property
    def thread_context(self) -> Optional[Dict[str, Any]]:
        return self.threadContext

    @property
    def pull_request_thread_context(self) -> Optional[Dict[str, Any]]:
        return self.pullRequestThreadContext


class PullRequestCommentsResponse(BaseModel):
    """Response from get PR comments operation"""

    success: bool
    data: Optional[List[PullRequestThread]] = None
    count: Optional[int] = None  # Total count of threads
    error: Optional[str] = None
    raw_output: Optional[str] = None


class PullRequestCommentResponse(BaseModel):
    """Response from comment operations (add, update, resolve)"""

    success: bool
    data: Optional[Union[PullRequestComment, PullRequestThread]] = None
    error: Optional[str] = None
    raw_output: Optional[str] = None


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


class WorkItem(BaseModel):
    """Work item information"""

    id: int
    title: str
    work_item_type: str
    state: str
    assigned_to: Optional[PullRequestIdentity] = None
    created_by: Optional[PullRequestIdentity] = None
    created_date: Optional[datetime] = None
    changed_date: Optional[datetime] = None
    area_path: Optional[str] = None
    iteration_path: Optional[str] = None
    description: Optional[str] = None
    reason: Optional[str] = None
    priority: Optional[int] = None
    severity: Optional[str] = None
    tags: Optional[str] = None
    url: Optional[str] = None
    fields: Optional[Dict[str, Any]] = Field(default_factory=dict)
    relations: Optional[List[Dict[str, Any]]] = Field(default_factory=list)


class WorkItemResponse(BaseModel):
    """Response from get work item operation"""

    success: bool
    data: Optional[WorkItem] = None
    error: Optional[str] = None
    raw_output: Optional[str] = None


class WorkItemCreateResponse(BaseModel):
    """Response from create work item operation"""

    success: bool
    data: Optional[WorkItem] = None
    error: Optional[str] = None
    raw_output: Optional[str] = None


class WorkItemUpdateResponse(BaseModel):
    """Response from update work item operation"""

    success: bool
    data: Optional[WorkItem] = None
    error: Optional[str] = None
    raw_output: Optional[str] = None
