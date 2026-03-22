import os

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse

from app.agent import CopilotService, get_copilot_service
from app.dashboard import build_dashboard
from app.mcp import (
    MCPSessionData,
    MCPSessionStore,
    NotionMCPClient,
    get_mcp_session_store,
    get_notion_mcp_client,
)
from app.notion_client import NotionService, get_notion_service
from app.reviews import default_quick_actions
from app.schemas import (
    AppConfigResponse,
    ChatMessage,
    DashboardResponse,
    FollowUpDraftResponse,
    FollowUpNoteCreate,
    LogHours,
    MCPStatusResponse,
    ProjectCreate,
    QuickAction,
    RescuePlanResponse,
    ReviewResponse,
)

router = APIRouter()


def get_mcp_session(
    request: Request,
    session_store: MCPSessionStore = Depends(get_mcp_session_store),
) -> MCPSessionData:
    return session_store.get_or_create(request.cookies.get("copilot_session"))


@router.get("/app-config", response_model=AppConfigResponse)
def app_config(
    notion_service: NotionService = Depends(get_notion_service),
    mcp_session: MCPSessionData = Depends(get_mcp_session),
):
    return {
        "demo_mode": notion_service.demo_mode,
        "mcp_connected": mcp_session.connected,
    }


@router.get("/mcp/status", response_model=MCPStatusResponse)
def mcp_status(
    mcp_session: MCPSessionData = Depends(get_mcp_session),
    mcp_client: NotionMCPClient = Depends(get_notion_mcp_client),
):
    return {
        "connected": mcp_session.connected,
        "server_url": mcp_client.server_url,
        "tools_available": len(mcp_session.last_tools),
    }


@router.get("/mcp/connect")
def mcp_connect(
    request: Request,
    mcp_session: MCPSessionData = Depends(get_mcp_session),
    mcp_client: NotionMCPClient = Depends(get_notion_mcp_client),
):
    redirect_uri = str(request.url_for("mcp_callback"))
    authorization_url = mcp_client.build_authorization_url(mcp_session, redirect_uri)
    response = RedirectResponse(url=authorization_url, status_code=302)
    response.set_cookie(
        "copilot_session",
        mcp_session.session_id,
        httponly=True,
        samesite="lax",
    )
    return response


@router.get("/mcp/callback", name="mcp_callback")
def mcp_callback(
    request: Request,
    code: str,
    state: str,
    session_store: MCPSessionStore = Depends(get_mcp_session_store),
    mcp_client: NotionMCPClient = Depends(get_notion_mcp_client),
):
    session = session_store.find_by_state(state)
    if not session:
        raise HTTPException(status_code=400, detail="Unknown OAuth state")

    redirect_uri = str(request.url_for("mcp_callback"))
    mcp_client.exchange_code(session, code, redirect_uri)
    frontend_url = os.getenv("FRONTEND_URL", "http://127.0.0.1:5173")
    response = RedirectResponse(url=f"{frontend_url}?mcp=connected", status_code=302)
    response.set_cookie(
        "copilot_session",
        session.session_id,
        httponly=True,
        samesite="lax",
    )
    return response


@router.post("/mcp/disconnect")
def mcp_disconnect(
    mcp_session: MCPSessionData = Depends(get_mcp_session),
    session_store: MCPSessionStore = Depends(get_mcp_session_store),
):
    session_store.reset_connection(mcp_session)
    return {"message": "Notion MCP disconnected"}


@router.post("/chat")
def chat(
    data: ChatMessage,
    copilot_service: CopilotService = Depends(get_copilot_service),
    mcp_session: MCPSessionData = Depends(get_mcp_session),
):
    return {"response": copilot_service.reply(data.message, mcp_session=mcp_session)}


@router.get("/projects")
def list_projects(notion_service: NotionService = Depends(get_notion_service)):
    return notion_service.get_projects()


@router.get("/dashboard", response_model=DashboardResponse)
def dashboard(notion_service: NotionService = Depends(get_notion_service)):
    return build_dashboard(notion_service.get_projects())


@router.get("/copilot/actions", response_model=list[QuickAction])
def quick_actions():
    return default_quick_actions()


@router.get("/copilot/weekly-review", response_model=ReviewResponse)
def weekly_review(
    copilot_service: CopilotService = Depends(get_copilot_service),
):
    return copilot_service.weekly_review()


@router.get("/copilot/follow-up/{project_id}", response_model=FollowUpDraftResponse)
def follow_up_draft(
    project_id: str,
    copilot_service: CopilotService = Depends(get_copilot_service),
):
    try:
        return copilot_service.draft_follow_up(project_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/copilot/rescue/{project_id}", response_model=RescuePlanResponse)
def rescue_plan(
    project_id: str,
    copilot_service: CopilotService = Depends(get_copilot_service),
):
    try:
        return copilot_service.rescue_plan(project_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/projects", status_code=201)
def add_project(
    data: ProjectCreate,
    notion_service: NotionService = Depends(get_notion_service),
):
    notion_service.create_project(data.client, data.budget, data.deadline, data.hours)
    return {"message": "Project created successfully"}


@router.post("/log-hours")
def add_hours(
    data: LogHours,
    notion_service: NotionService = Depends(get_notion_service),
):
    notion_service.log_hours(data.project_id, data.hours)
    return {"message": "Hours logged successfully"}


@router.post("/follow-up-note")
def add_follow_up_note(
    data: FollowUpNoteCreate,
    notion_service: NotionService = Depends(get_notion_service),
):
    notion_service.create_follow_up_note(data.project_id, data.content)
    return {"message": "Follow-up note saved successfully"}


@router.get("/invoice/{project_id}")
def generate_invoice(
    project_id: str,
    notion_service: NotionService = Depends(get_notion_service),
):
    projects = notion_service.get_projects()
    project = next((project for project in projects if project["id"] == project_id), None)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    invoice = f"""
    INVOICE
    -------
    Client: {project["name"]}
    Total Hours: {project["hours"]}
    Budget: EUR {project["budget"]}
    Deadline: {project["deadline"]}
    Status: {project["status"]}
    -------
    Total: EUR {project["budget"]}
    """
    return {"invoice": invoice}
