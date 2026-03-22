import unittest
from datetime import date, timedelta

from app.reviews import build_weekly_review, default_quick_actions


class ReviewsTests(unittest.TestCase):
    def test_default_quick_actions_have_expected_prompts(self):
        actions = default_quick_actions()

        self.assertEqual(actions[0].id, "today-focus")
        self.assertIn("weekly review", actions[1].prompt.lower())

    def test_weekly_review_summarizes_project_health(self):
        projects = [
            {
                "id": "1",
                "name": "Acme",
                "client": "Acme",
                "budget": 1000,
                "deadline": (date.today() + timedelta(days=2)).isoformat(),
                "status": "Active",
                "hours": 15,
                "last_update": date.today().isoformat(),
            },
            {
                "id": "2",
                "name": "Beta",
                "client": "Beta",
                "budget": 4000,
                "deadline": (date.today() + timedelta(days=20)).isoformat(),
                "status": "Active",
                "hours": 5,
                "last_update": date.today().isoformat(),
            },
        ]

        review = build_weekly_review(projects)

        self.assertEqual(review.title, "Weekly Portfolio Review")
        self.assertIn("2 projects", review.summary)
        self.assertTrue(review.risks)
        self.assertTrue(review.next_steps)


if __name__ == "__main__":
    unittest.main()
