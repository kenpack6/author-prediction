import unittest
from fastapi.testclient import TestClient
from author_prediction.server import app


class TestServer(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_read_root(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"message": "Hello, World!"})


if __name__ == "__main__":
    unittest.main()
