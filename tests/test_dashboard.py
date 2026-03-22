import unittest
from datetime import date, timedelta

from app.dashboard import build_dashboard


def _project(
    project_id: str,
    name: str,
    budget: float,
    hours: float,
    deadline_offset_days: int,
    status: str = "Active",
):
    return {
        "id": project_id,
        "name": name,
        "client": name,
        "budget": budget,
        "deadline": (date.today() + timedelta(days=deadline_offset_days)).isoformat(),
        "status": status,
        "hours": hours,
        "last_update": date.today().isoformat(),
    }


class DashboardTests(unittest.TestCase):
    def test_dashboard_marks_urgent_and_at_risk_projects(self):
        projects = [
            _project("1", "Acme", 1000, 15, 2),
            _project("2", "Beta", 4000, 8, 14),
            _project("3", "Gamma", 500, 3, -1, status="Blocked"),
        ]

        dashboard = build_dashboard(projects)

        self.assertEqual(dashboard.summary.total_projects, 3)
        self.assertEqual(dashboard.summary.active_projects, 2)
        self.assertEqual(dashboard.summary.urgent_count, 2)
        self.assertEqual(dashboard.summary.at_risk_count, 2)
        self.assertEqual(dashboard.projects[0].project.name, "Gamma")
        self.assertTrue(any(risk.label == "Overdue" for risk in dashboard.projects[0].risks))

    def test_dashboard_keeps_healthy_project_low_risk(self):
        projects = [_project("1", "Healthy", 3000, 4, 20)]

        dashboard = build_dashboard(projects)

        self.assertEqual(dashboard.summary.urgent_count, 0)
        self.assertEqual(dashboard.summary.at_risk_count, 0)
        self.assertEqual(dashboard.projects[0].risk_score, 0)
        self.assertEqual(dashboard.projects[0].risks[0].label, "Healthy")


if __name__ == "__main__":
    unittest.main()
