import os
from copy import deepcopy
from datetime import date, timedelta
from typing import Any, Dict, List, Optional
from uuid import uuid4

from dotenv import load_dotenv
from notion_client import Client

load_dotenv()


def _safe_title_value(property_value: Dict[str, Any]) -> str:
    title = property_value.get("title", [])
    if not title:
        return ""
    return title[0].get("text", {}).get("content", "")


def _safe_rich_text_value(property_value: Dict[str, Any]) -> str:
    rich_text = property_value.get("rich_text", [])
    if not rich_text:
        return ""
    return rich_text[0].get("text", {}).get("content", "")


def _demo_projects() -> List[Dict[str, Any]]:
    today = date.today()
    return [
        {
            "id": "demo-acme",
            "name": "Acme Website Refresh",
            "client": "Acme",
            "budget": 2400,
            "deadline": (today + timedelta(days=2)).isoformat(),
            "status": "Active",
            "hours": 19,
            "last_update": today.isoformat(),
        },
        {
            "id": "demo-northstar",
            "name": "Northstar Landing Page",
            "client": "Northstar",
            "budget": 1600,
            "deadline": (today + timedelta(days=6)).isoformat(),
            "status": "Active",
            "hours": 11,
            "last_update": today.isoformat(),
        },
        {
            "id": "demo-orbit",
            "name": "Orbit Product Copy",
            "client": "Orbit",
            "budget": 900,
            "deadline": (today + timedelta(days=14)).isoformat(),
            "status": "Active",
            "hours": 4,
            "last_update": today.isoformat(),
        },
    ]


class NotionService:
    def __init__(
        self,
        notion_client: Optional[Client] = None,
        database_id: Optional[str] = None,
        demo_mode: Optional[bool] = None,
    ) -> None:
        self._client = notion_client or Client(auth=os.getenv("NOTION_TOKEN"))
        self._database_id = database_id or os.getenv("NOTION_DATABASE_ID")
        self._demo_mode = (
            demo_mode
            if demo_mode is not None
            else os.getenv("DEMO_MODE", "").lower() in {"1", "true", "yes"}
        )
        self._demo_projects = deepcopy(_demo_projects())
        self._demo_notes: Dict[str, List[str]] = {}

    @property
    def demo_mode(self) -> bool:
        return self._demo_mode

    def create_project(
        self,
        client: str,
        budget: float,
        deadline: str,
        hours: float = 0,
    ) -> None:
        if self._demo_mode:
            self._demo_projects.append(
                {
                    "id": f"demo-{uuid4().hex[:8]}",
                    "name": client,
                    "client": client,
                    "budget": budget,
                    "deadline": deadline,
                    "status": "Active",
                    "hours": hours,
                    "last_update": date.today().isoformat(),
                }
            )
            return

        self._client.pages.create(
            parent={"database_id": self._database_id},
            properties={
                "Name": {"title": [{"text": {"content": client}}]},
                "Client": {"rich_text": [{"text": {"content": client}}]},
                "Budget": {"number": budget},
                "Deadline": {"date": {"start": deadline}},
                "Status": {"select": {"name": "Active"}},
                "Hours": {"number": hours},
            },
        )

    def get_projects(self) -> List[Dict[str, Any]]:
        if self._demo_mode:
            return deepcopy(self._demo_projects)

        try:
            response = self._client.databases.query(database_id=self._database_id)
        except Exception:
            self._demo_mode = True
            return deepcopy(self._demo_projects)

        results = []
        for page in response.get("results", []):
            props = page.get("properties", {})
            deadline = props.get("Deadline", {}).get("date")
            status = props.get("Status", {}).get("select")
            hours = props.get("Hours", {}).get("number")
            budget = props.get("Budget", {}).get("number")
            client_name = _safe_rich_text_value(props.get("Client", {}))
            name = _safe_title_value(props.get("Name", {}))

            results.append(
                {
                    "id": page.get("id", ""),
                    "name": name or client_name,
                    "client": client_name or name,
                    "budget": budget or 0,
                    "deadline": deadline.get("start") if deadline else None,
                    "status": status.get("name") if status else "Unknown",
                    "hours": hours or 0,
                    "last_update": self._get_last_update(props),
                }
            )
        return results

    def log_hours(self, project_id: str, hours: float) -> None:
        if self._demo_mode:
            project = self._find_demo_project(project_id)
            project["hours"] += hours
            project["last_update"] = date.today().isoformat()
            return

        page = self._client.pages.retrieve(page_id=project_id)
        current_hours = page.get("properties", {}).get("Hours", {}).get("number") or 0
        self._client.pages.update(
            page_id=project_id,
            properties={
                "Hours": {"number": current_hours + hours},
            },
        )

    def create_follow_up_note(self, project_id: str, content: str) -> None:
        if self._demo_mode:
            self._find_demo_project(project_id)["last_update"] = date.today().isoformat()
            self._demo_notes.setdefault(project_id, []).append(content)
            return

        self._client.blocks.children.append(
            block_id=project_id,
            children=[
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {"content": content},
                            }
                        ]
                    },
                }
            ],
        )

    def _find_demo_project(self, project_id: str) -> Dict[str, Any]:
        project = next((item for item in self._demo_projects if item["id"] == project_id), None)
        if not project:
            raise ValueError("Project not found")
        return project

    @staticmethod
    def _get_last_update(properties: Dict[str, Any]) -> Optional[str]:
        if "Last Update" in properties:
            date_property = properties["Last Update"].get("date")
            if date_property:
                return date_property.get("start")

        if "Updated" in properties:
            date_property = properties["Updated"].get("date")
            if date_property:
                return date_property.get("start")

        return date.today().isoformat()


_notion_service = NotionService()


def get_notion_service() -> NotionService:
    return _notion_service
