import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from api import app

client = TestClient(app)


class TestWeeklyAdAPI(unittest.TestCase):
    def test_get_weekly_ad_success(self):
        class DummyCursor:
            def __init__(self):
                self.params = None

            def execute(self, query, params):
                self.params = params

            def fetchall(self):
                if self.params == ("Kroger", "2025-09-01"):
                    return [
                        ("Bananas", 0.59, b"\x89PNG..."),
                        ("Apples", 1.29, None),
                    ]
                return []

        class DummyConn:
            def __init__(self):
                self._cursor = DummyCursor()

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc_val, exc_tb):
                pass

            def cursor(self):
                return self._cursor

        with patch("api.get_connection", return_value=DummyConn()):
            response = client.get("/weeklyad/?storename=Kroger&week=2025-09-01")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIsInstance(data, list)
            self.assertEqual(data[0]["product"], "Bananas")
            self.assertIsNotNone(data[0]["image_base64"])
            self.assertEqual(data[1]["product"], "Apples")
            self.assertIsNone(data[1]["image_base64"])

    def test_get_weekly_ad_not_found(self):
        class DummyCursor:
            def execute(self, query, params):
                pass

            def fetchall(self):
                return []

        class DummyConn:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc_val, exc_tb):
                pass

            def cursor(self):
                return DummyCursor()

        with patch("api.get_connection", return_value=DummyConn()):
            response = client.get("/weeklyad/?storename=Kroger&week=2025-09-01")
            self.assertEqual(response.status_code, 404)
            self.assertEqual(
                response.json()["detail"], "No weekly ad found for this store and week."
            )


if __name__ == "__main__":
    unittest.main()
