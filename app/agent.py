import json
import os
from typing import Any, Dict, List, Optional
from urllib import error, request

from dotenv import load_dotenv

from app.dashboard import build_dashboard
from app.mcp import MCPSessionData, NotionMCPClient, get_notion_mcp_client
from app.notion_client import NotionService, get_notion_service
from app.reviews import build_rescue_plan, build_weekly_review

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent"
)


def _agent_unavailable_message(details: str = "") -> str:
    suffix = f" Details: {details}" if details else ""
    return (
        "The AI chat assistant is currently unavailable because Gemini is not "
        "configured correctly or the API request failed. You can still use the "
        f"direct project endpoints like /projects and /log-hours.{suffix}"
    )


def _build_system_prompt(message: str, projects: List[Dict], use_mcp: bool) -> str:
    dashboard = build_dashboard(projects)
    context = {
        "summary": dashboard.summary.model_dump(),
        "projects": [project.model_dump() for project in dashboard.projects[:8]],
    }
    mode_line = (
        "Use the connected Notion MCP tools when you need live workspace data or write actions.\n"
        if use_mcp
        else ""
    )
    return (
        "You are Freelance OS Copilot, an assistant for a freelancer using Notion.\n"
        "Answer clearly and briefly.\n"
        "When useful, mention urgent projects, budget pressure, or next actions.\n"
        "If the user asks for something outside the available data, say what is missing.\n"
        f"{mode_line}"
        f"Today's date is {os.getenv('CURRENT_DATE', '2026-03-21')}.\n"
        f"Workspace context: {json.dumps(context, ensure_ascii=True)}\n"
        f"User message: {message}"
    )


def _gemini_request(contents: list, tools: Optional[list] = None) -> Dict:
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is missing")

    payload: dict[str, Any] = {"contents": contents}
    if tools:
        payload["tools"] = [{"functionDeclarations": tools}]

    req = request.Request(
        GEMINI_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": GEMINI_API_KEY,
        },
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(details) from exc
    except error.URLError as exc:
        raise RuntimeError(str(exc)) from exc


def _extract_text(response: Dict) -> str:
    candidates = response.get("candidates", [])
    if not candidates:
        return ""
    parts = candidates[0].get("content", {}).get("parts", [])
    text_parts = [part.get("text", "") for part in parts if part.get("text")]
    return "\n".join(text_parts).strip()


def _extract_function_call(response: Dict) -> Optional[dict]:
    candidates = response.get("candidates", [])
    if not candidates:
        return None
    for part in candidates[0].get("content", {}).get("parts", []):
        if "functionCall" in part:
            return part["functionCall"]
    return None


def _mcp_tools_to_gemini(tool_payload: list[dict]) -> list[dict]:
    return [
        {
            "name": tool["name"],
            "description": tool.get("description", ""),
            "parameters": tool.get("inputSchema", {"type": "object", "properties": {}}),
        }
        for tool in tool_payload
    ]


def _stringify_tool_result(result: dict) -> str:
    return json.dumps(result, ensure_ascii=True)


class CopilotService:
    def __init__(
        self,
        notion_service: Optional[NotionService] = None,
        mcp_client: Optional[NotionMCPClient] = None,
    ) -> None:
        self._notion_service = notion_service or get_notion_service()
        self._mcp_client = mcp_client or get_notion_mcp_client()

    def reply(
        self,
        message: str,
        mcp_session: Optional[MCPSessionData] = None,
    ) -> str:
        projects = self._notion_service.get_projects()
        use_mcp = bool(mcp_session and mcp_session.connected)

        if use_mcp:
            try:
                return self._reply_with_mcp(message, projects, mcp_session)
            except RuntimeError as exc:
                return self._fallback_reply(message, projects, str(exc)[:240])

        prompt = _build_system_prompt(message, projects, use_mcp=False)
        try:
            response = _gemini_request(
                [{"role": "user", "parts": [{"text": prompt}]}],
            )
        except RuntimeError as exc:
            return self._fallback_reply(message, projects, str(exc)[:240])

        return _extract_text(response) or _agent_unavailable_message()

    def weekly_review(self) -> dict:
        return build_weekly_review(self._notion_service.get_projects()).model_dump()

    def rescue_plan(self, project_id: str) -> dict:
        return build_rescue_plan(
            self._notion_service.get_projects(),
            project_id,
        ).model_dump()

    def draft_follow_up(self, project_id: str) -> dict:
        projects = self._notion_service.get_projects()
        project = next((item for item in projects if item["id"] == project_id), None)
        if not project:
            raise ValueError("Project not found")

        dashboard = build_dashboard(projects)
        insight = next(
            (item for item in dashboard.projects if item.project.id == project_id),
            None,
        )
        top_risk = insight.risks[0].reason if insight else "No major risks flagged."
        draft = (
            f"Hi {project['client']},\n\n"
            f"Quick update on {project['name']}: I am actively working on it. "
            f"Current status is {project['status']}. "
            f"Main point to watch: {top_risk} "
            f"My next step is to {insight.suggested_action.lower() if insight else 'keep delivery moving'}.\n\n"
            "Let me know if you want any priority changes.\n"
        )
        return {
            "project_id": project_id,
            "project_name": project["name"],
            "draft": draft,
        }

    def _reply_with_mcp(
        self,
        message: str,
        projects: List[Dict],
        mcp_session: MCPSessionData,
    ) -> str:
        tools = self._mcp_client.list_tools(mcp_session)
        gemini_tools = _mcp_tools_to_gemini(tools)
        contents = [
            {
                "role": "user",
                "parts": [{"text": _build_system_prompt(message, projects, use_mcp=True)}],
            }
        ]

        for _ in range(5):
            response = _gemini_request(contents, tools=gemini_tools)
            function_call = _extract_function_call(response)
            if not function_call:
                return _extract_text(response) or _agent_unavailable_message()

            tool_name = function_call.get("name")
            tool_args = function_call.get("args", {})
            tool_result = self._mcp_client.call_tool(mcp_session, tool_name, tool_args)

            contents.extend(
                [
                    {"role": "model", "parts": [{"functionCall": function_call}]},
                    {
                        "role": "user",
                        "parts": [
                            {
                                "functionResponse": {
                                    "name": tool_name,
                                    "response": {"result": _stringify_tool_result(tool_result)},
                                }
                            }
                        ],
                    },
                ]
            )

        raise RuntimeError("MCP tool loop exceeded the safe recursion limit")

    def _fallback_reply(self, message: str, projects: List[Dict], details: str) -> str:
        normalized = message.lower()
        dashboard = build_dashboard(projects)

        if "weekly" in normalized and "review" in normalized:
            review = build_weekly_review(projects)
            return (
                f"{review.title}\n"
                f"{review.summary}\n"
                f"Wins: {'; '.join(review.wins)}\n"
                f"Risks: {'; '.join(review.risks)}\n"
                f"Next: {'; '.join(review.next_steps)}"
            )

        if "rescue" in normalized:
            risky_project = next(iter(dashboard.at_risk_projects), None)
            if not risky_project:
                return "No project currently needs rescue mode. The portfolio looks stable."
            rescue = build_rescue_plan(projects, risky_project.project.id)
            return (
                f"{rescue.headline}\n"
                f"{rescue.summary}\n"
                f"Plan: {'; '.join(rescue.internal_plan)}\n"
                f"Client update: {rescue.client_update}"
            )

        if "attention" in normalized or "focus" in normalized:
            urgent = dashboard.urgent_projects[:3]
            if not urgent:
                return "Nothing urgent is flagged today. Review the next deliverable and keep momentum."
            return "\n".join(
                f"- {insight.project.name}: {insight.risks[0].reason} Next: {insight.suggested_action}"
                for insight in urgent
            )

        return _agent_unavailable_message(details)


_copilot_service = CopilotService()


def get_copilot_service() -> CopilotService:
    return _copilot_service
