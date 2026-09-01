import unittest
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient
from author_prediction.server import app, get_db


class TestProjectsRouter(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.mock_db = MagicMock()
        app.dependency_overrides[get_db] = lambda: self.mock_db

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_list_projects(self):
        self.mock_db.fetch = AsyncMock(
            return_value=[{"id": 1, "name": "Project Alpha", "sources": 3}]
        )
        response = self.client.get("/projects/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            [{"id": 1, "name": "Project Alpha", "sources": 3}],
        )

    def test_create_project(self):
        self.mock_db.fetchrow = AsyncMock(return_value={"id": 1, "name": "Project Alpha"})
        payload = {"name": "Project Alpha"}
        response = self.client.post("/projects/", json=payload)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.json(),
            {"id": 1, "name": "Project Alpha", "sources": 0},
        )

    def test_get_project_by_id(self):
        self.mock_db.fetchrow = AsyncMock(
            return_value={"id": 1, "name": "Project Beta", "sources": 5}
        )
        response = self.client.get("/projects/1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"id": 1, "name": "Project Beta", "sources": 5},
        )

    def test_get_project_not_found(self):
        self.mock_db.fetchrow = AsyncMock(return_value=None)
        response = self.client.get("/projects/999")
        self.assertEqual(response.status_code, 404)

    def test_update_project(self):
        self.mock_db.fetchrow = AsyncMock(
            return_value={"id": 1, "name": "New Name", "sources": 2}
        )
        response = self.client.put("/projects/1", json={"name": "New Name"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"id": 1, "name": "New Name", "sources": 2},
        )

    def test_update_project_not_found(self):
        self.mock_db.fetchrow = AsyncMock(return_value=None)
        response = self.client.put("/projects/999", json={"name": "New Name"})
        self.assertEqual(response.status_code, 404)

    def test_delete_project(self):
        self.mock_db.execute = AsyncMock(return_value="DELETE 1")
        response = self.client.delete("/projects/1")
        self.assertEqual(response.status_code, 204)

    def test_delete_project_not_found(self):
        self.mock_db.execute = AsyncMock(return_value="DELETE 0")
        response = self.client.delete("/projects/999")
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
