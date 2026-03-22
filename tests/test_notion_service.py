import unittest

from app.notion_client import NotionService


class NotionServiceTests(unittest.TestCase):
    def test_demo_mode_supports_create_log_and_notes(self):
        service = NotionService(demo_mode=True)
        initial_count = len(service.get_projects())

        service.create_project("Demo Client", 1200, "2026-04-01", 2)
        projects = service.get_projects()
        self.assertEqual(len(projects), initial_count + 1)

        created = next(project for project in projects if project["name"] == "Demo Client")
        service.log_hours(created["id"], 3)
        updated = next(project for project in service.get_projects() if project["id"] == created["id"])
        self.assertEqual(updated["hours"], 5)

        service.create_follow_up_note(created["id"], "Sent kickoff recap.")
        self.assertTrue(service.demo_mode)


if __name__ == "__main__":
    unittest.main()
