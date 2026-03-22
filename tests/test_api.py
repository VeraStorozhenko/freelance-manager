import unittest
from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.agent import get_copilot_service
from app.main import app
from app.mcp import MCPSessionData
from app.notion_client import get_notion_service
from app.routers import get_mcp_session


class FakeNotionService:
    def __init__(self):
        self.demo_mode = True
        self.projects = [
            {
                "id": "project-1",
                "name": "Acme Website",
                "client": "Acme",
                "budget": 1200,
                "deadline": (date.today() + timedelta(days=2)).isoformat(),
                "status": "Active",
                "hours": 14,
                "last_update": date.today().isoformat(),
            },
            {
                "id": "project-2",
                "name": "Beta Retainer",
                "client": "Beta",
                "budget": 3000,
                "deadline": (date.today() + timedelta(days=10)).isoformat(),
                "status": "Active",
                "hours": 8,
                "last_update": date.today().isoformat(),
            },
        ]
        self.created_projects = []
        self.logged_hours = []
        self.follow_up_notes = []

    def get_projects(self):
        return self.projects

    def create_project(self, client, budget, deadline, hours=0):
        self.created_projects.append(
            {
                "client": client,
                "budget": budget,
                "deadline": deadline,
                "hours": hours,
            }
        )

    def log_hours(self, project_id, hours):
        self.logged_hours.append({"project_id": project_id, "hours": hours})

    def create_follow_up_note(self, project_id, content):
        self.follow_up_notes.append({"project_id": project_id, "content": content})


class FakeCopilotService:
    def reply(self, message: str, mcp_session=None) -> str:
        return f"copilot:{message}"

    def weekly_review(self) -> dict:
        return {
            "title": "Weekly Portfolio Review",
            "summary": "Two projects are active, one is urgent.",
            "wins": ["Beta Retainer is on track."],
            "risks": ["Acme Website deadline is in 2 days."],
            "next_steps": ["Send an update to Acme today."],
        }

    def draft_follow_up(self, project_id: str) -> dict:
        if project_id != "project-1":
            raise ValueError("Project not found")
        return {
            "project_id": "project-1",
            "project_name": "Acme Website",
            "draft": "Hi Acme,\n\nQuick update on Acme Website.\n",
        }

    def rescue_plan(self, project_id: str) -> dict:
        if project_id != "project-1":
            raise ValueError("Project not found")
        return {
            "project_id": "project-1",
            "project_name": "Acme Website",
            "headline": "Project Rescue Mode: immediate intervention recommended",
            "summary": "Acme Website has a risk score of 5.",
            "risks": ["The deadline is in 2 day(s)."],
            "internal_plan": ["Move the risky milestone first."],
            "client_update": "Hi Acme, I reviewed the timeline.",
            "immediate_action": "Send a client update and confirm the next milestone.",
        }


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.fake_notion = FakeNotionService()
        app.dependency_overrides[get_notion_service] = lambda: self.fake_notion
        app.dependency_overrides[get_copilot_service] = lambda: FakeCopilotService()
        app.dependency_overrides[get_mcp_session] = lambda: MCPSessionData(
            session_id="test-session",
            access_token=None,
        )
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_dashboard_endpoint_returns_summary_and_projects(self):
        response = self.client.get("/dashboard")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["summary"]["total_projects"], 2)
        self.assertEqual(len(payload["projects"]), 2)
        self.assertEqual(payload["projects"][0]["project"]["name"], "Acme Website")

    def test_app_config_endpoint_reports_demo_mode(self):
        response = self.client.get("/app-config")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["demo_mode"])
        self.assertFalse(response.json()["mcp_connected"])

    def test_mcp_status_endpoint_returns_disconnected_by_default(self):
        response = self.client.get("/mcp/status")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertFalse(payload["connected"])
        self.assertIn("mcp.notion.com", payload["server_url"])

    def test_chat_endpoint_uses_copilot_dependency(self):
        response = self.client.post("/chat", json={"message": "What needs attention today?"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["response"],
            "copilot:What needs attention today?",
        )

    def test_create_project_endpoint_delegates_to_notion_service(self):
        response = self.client.post(
            "/projects",
            json={
                "client": "Delta",
                "budget": 900,
                "deadline": "2026-03-30",
                "hours": 2,
            },
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(self.fake_notion.created_projects[0]["client"], "Delta")

    def test_quick_actions_endpoint_returns_seed_actions(self):
        response = self.client.get("/copilot/actions")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertGreaterEqual(len(payload), 3)
        self.assertEqual(payload[0]["id"], "today-focus")

    def test_weekly_review_endpoint_uses_copilot_dependency(self):
        response = self.client.get("/copilot/weekly-review")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["title"], "Weekly Portfolio Review")
        self.assertEqual(payload["next_steps"][0], "Send an update to Acme today.")

    def test_follow_up_draft_endpoint_returns_generated_copy(self):
        response = self.client.get("/copilot/follow-up/project-1")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["project_name"], "Acme Website")
        self.assertIn("Quick update", payload["draft"])

    def test_rescue_plan_endpoint_returns_rescue_workflow(self):
        response = self.client.get("/copilot/rescue/project-1")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["project_name"], "Acme Website")
        self.assertIn("Rescue Mode", payload["headline"])
        self.assertTrue(payload["internal_plan"])

    def test_rescue_plan_endpoint_returns_404_for_unknown_project(self):
        response = self.client.get("/copilot/rescue/missing")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Project not found")

    def test_follow_up_draft_endpoint_returns_404_for_unknown_project(self):
        response = self.client.get("/copilot/follow-up/missing")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Project not found")

    def test_log_hours_endpoint_delegates_to_notion_service(self):
        response = self.client.post(
            "/log-hours",
            json={"project_id": "project-1", "hours": 3},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.fake_notion.logged_hours[0]["hours"], 3)

    def test_follow_up_note_endpoint_delegates_to_notion_service(self):
        response = self.client.post(
            "/follow-up-note",
            json={"project_id": "project-1", "content": "Sent scope clarification."},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.fake_notion.follow_up_notes[0]["content"],
            "Sent scope clarification.",
        )

    def test_mcp_disconnect_endpoint_returns_success(self):
        response = self.client.post("/mcp/disconnect")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["message"], "Notion MCP disconnected")

    def test_invoice_endpoint_returns_404_for_unknown_project(self):
        response = self.client.get("/invoice/does-not-exist")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Project not found")


if __name__ == "__main__":
    unittest.main()
