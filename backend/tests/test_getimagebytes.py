import os
import tempfile
import base64
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from api import app

client = TestClient(app)


class TestGetImageBytes(unittest.TestCase):
    def test_get_image_bytes_success(self):
        # create a temporary folder and image file
        with tempfile.TemporaryDirectory() as tmpdir:
            fname = "test_image.png"
            data = b"\x89PNGTESTDATA"
            file_path = os.path.join(tmpdir, fname)
            with open(file_path, "wb") as f:
                f.write(data)

            with patch("crawler.utility.get_store_week_folder", return_value=tmpdir):
                response = client.get(
                    f"/getimagebytes/?storename=Kroger&week=2025-12-29&image_filename={fname}"
                )
                self.assertEqual(response.status_code, 200)
                expected_b64 = base64.b64encode(data).decode()
                self.assertEqual(response.json().get("image_bytes"), expected_b64)

    def test_get_image_bytes_not_found(self):
        # folder exists but file does not
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("crawler.utility.get_store_week_folder", return_value=tmpdir):
                response = client.get(
                    "/getimagebytes/?storename=Kroger&week=2025-12-29&image_filename=missing.png"
                )
                self.assertEqual(response.status_code, 404)
                self.assertEqual(response.json().get("detail"), "Image file not found.")


if __name__ == "__main__":
    unittest.main()
