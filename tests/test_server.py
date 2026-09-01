import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient
from author_prediction.server import app
from author_prediction.server.dependencies import DbConn, get_db



class TestServer(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_read_root(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"message": "Hello, World!"})

    def test_get_db_uninitialized(self):
        mock_request = MagicMock()
        mock_request.app.state.db_pool = None
        gen = get_db(mock_request)
        with self.assertRaises(RuntimeError):
            import asyncio
            asyncio.run(gen.__anext__())

    def test_db_conn_dependency_override(self):
        from author_prediction.server import DbConn

        @app.get("/test-db")
        async def test_db_endpoint(db: DbConn):
            return {"connected": True}

        mock_conn = MagicMock()
        app.dependency_overrides[get_db] = lambda: mock_conn
        try:
            response = self.client.get("/test-db")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), {"connected": True})
        finally:
            app.dependency_overrides.clear()


if __name__ == "__main__":
    unittest.main()


