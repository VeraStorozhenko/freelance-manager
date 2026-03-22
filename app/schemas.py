from typing import List, Optional

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    message: str = Field(..., min_length=1)


class ProjectCreate(BaseModel):
    client: str
    budget: float
    deadline: str
    hours: float = 0


class LogHours(BaseModel):
    project_id: str
    hours: float


class ProjectSummary(BaseModel):
    id: str
    name: str
    client: str
    budget: float
    deadline: Optional[str]
    status: str
    hours: float
    last_update: Optional[str] = None


class ProjectRisk(BaseModel):
    label: str
    severity: str
    reason: str


class ProjectInsight(BaseModel):
    project: ProjectSummary
    risk_score: int
    risks: List[ProjectRisk]
    suggested_action: str


class DashboardSummary(BaseModel):
    total_projects: int
    active_projects: int
    total_budget: float
    total_hours: float
    urgent_count: int
    at_risk_count: int


class DashboardResponse(BaseModel):
    summary: DashboardSummary
    urgent_projects: List[ProjectInsight]
    at_risk_projects: List[ProjectInsight]
    projects: List[ProjectInsight]


class QuickAction(BaseModel):
    id: str
    title: str
    prompt: str
    description: str


class ReviewResponse(BaseModel):
    title: str
    summary: str
    wins: List[str]
    risks: List[str]
    next_steps: List[str]


class FollowUpNoteCreate(BaseModel):
    project_id: str
    content: str = Field(..., min_length=1)


class FollowUpDraftResponse(BaseModel):
    project_id: str
    project_name: str
    draft: str


class AppConfigResponse(BaseModel):
    demo_mode: bool
    mcp_connected: bool


class MCPStatusResponse(BaseModel):
    connected: bool
    server_url: str
    tools_available: int = 0


class RescuePlanResponse(BaseModel):
    project_id: str
    project_name: str
    headline: str
    summary: str
    risks: List[str]
    internal_plan: List[str]
    client_update: str
    immediate_action: str
