import unittest
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient
from author_prediction.server import app, get_db


class TestSourcesRouter(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.mock_db = MagicMock()
        app.dependency_overrides[get_db] = lambda: self.mock_db

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_list_sources(self):
        self.mock_db.fetch = AsyncMock(
            return_value=[
                {
                    "id": 1,
                    "filename": "doc1.txt",
                    "processed_date": None,
                    "project": 10,
                }
            ]
        )
        response = self.client.get("/projects/10/sources/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            [
                {
                    "id": 1,
                    "filename": "doc1.txt",
                    "processed_date": None,
                    "project": 10,
                }
            ],
        )
        self.mock_db.fetch.assert_called_once_with(
            "SELECT id, filename, processed_date, project FROM sources WHERE project = $1 ORDER BY id",
            10,
        )

    def test_create_source(self):
        self.mock_db.fetchrow = AsyncMock(
            return_value={
                "id": 1,
                "filename": "doc1.txt",
                "full_text": "Sample text",
                "processed_date": None,
                "project": 10,
            }
        )
        payload = {"filename": "doc1.txt", "full_text": "Sample text"}
        response = self.client.post("/projects/10/sources/", json=payload)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.json(),
            {
                "id": 1,
                "filename": "doc1.txt",
                "full_text": "Sample text",
                "processed_date": None,
                "project": 10,
            },
        )

    def test_get_source_by_id(self):
        self.mock_db.fetchrow = AsyncMock(
            return_value={
                "id": 1,
                "filename": "doc1.txt",
                "full_text": "Sample text",
                "processed_date": None,
                "project": 10,
            }
        )
        response = self.client.get("/projects/10/sources/1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "id": 1,
                "filename": "doc1.txt",
                "full_text": "Sample text",
                "processed_date": None,
                "project": 10,
            },
        )

    def test_get_source_not_found(self):
        self.mock_db.fetchrow = AsyncMock(return_value=None)
        response = self.client.get("/projects/10/sources/999")
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()

