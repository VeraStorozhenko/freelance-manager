import unittest
from datetime import date, timedelta

from app.reviews import build_rescue_plan, default_quick_actions


class RescueTests(unittest.TestCase):
    def test_quick_actions_include_project_rescue(self):
        actions = default_quick_actions()
        self.assertTrue(any(action.id == "project-rescue" for action in actions))

    def test_build_rescue_plan_for_risky_project(self):
        projects = [
            {
                "id": "1",
                "name": "Acme",
                "client": "Acme",
                "budget": 1000,
                "deadline": (date.today() + timedelta(days=2)).isoformat(),
                "status": "Active",
                "hours": 14,
                "last_update": date.today().isoformat(),
            }
        ]

        rescue = build_rescue_plan(projects, "1")

        self.assertEqual(rescue.project_name, "Acme")
        self.assertIn("risk score", rescue.summary)
        self.assertTrue(rescue.internal_plan)
        self.assertIn("Hi Acme", rescue.client_update)

    def test_build_rescue_plan_raises_for_missing_project(self):
        with self.assertRaises(ValueError):
            build_rescue_plan([], "missing")


if __name__ == "__main__":
    unittest.main()
