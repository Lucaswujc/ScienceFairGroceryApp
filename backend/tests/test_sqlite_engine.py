import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db_engine import sqlite_engine


class TestSQLiteEngine(unittest.TestCase):
    """Test cases for the sqlite_engine module."""

    def setUp(self):
        """Set up test environment before each test."""
        # Create a temporary directory for test database
        self.test_dir = tempfile.mkdtemp()
        self.test_db_path = Path(self.test_dir) / "test_crawler_results.db"

        # Patch the DB_PATH to use our test database
        self.original_db_path = sqlite_engine.DB_PATH
        sqlite_engine.DB_PATH = self.test_db_path

    def tearDown(self):
        """Clean up after each test."""
        # Restore original DB_PATH
        sqlite_engine.DB_PATH = self.original_db_path

        # Remove test database if it exists
        if self.test_db_path.exists():
            self.test_db_path.unlink()

        # Remove test directory
        Path(self.test_dir).rmdir()

    def test_db_exists_returns_false_when_no_db(self):
        """Test db_exists returns False when database doesn't exist."""
        self.assertFalse(sqlite_engine.db_exists())

    def test_db_exists_returns_true_when_db_exists(self):
        """Test db_exists returns True when database exists."""
        # Create an empty file
        self.test_db_path.touch()
        self.assertTrue(sqlite_engine.db_exists())

    def test_init_db_creates_database(self):
        """Test init_db creates the database file."""
        sqlite_engine.init_db()
        self.assertTrue(self.test_db_path.exists())

    def test_init_db_creates_table(self):
        """Test init_db creates the crawler_results table with correct schema."""
        sqlite_engine.init_db()

        with sqlite3.connect(str(self.test_db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='crawler_results'"
            )
            result = cursor.fetchone()

        self.assertIsNotNone(result)
        table_sql = result[0]

        # Check that all expected columns are in the table definition
        self.assertIn("id INTEGER PRIMARY KEY AUTOINCREMENT", table_sql)
        self.assertIn("storename TEXT NOT NULL", table_sql)
        self.assertIn("weekly_ad_starting_date TEXT NOT NULL", table_sql)
        self.assertIn("product TEXT NOT NULL", table_sql)
        self.assertIn("image_url TEXT", table_sql)
        self.assertIn("image BLOB", table_sql)
        self.assertIn("price TEXT NOT NULL", table_sql)

    def test_get_connection_initializes_db_if_not_exists(self):
        """Test get_connection initializes database if it doesn't exist."""
        self.assertFalse(self.test_db_path.exists())
        conn = sqlite_engine.get_connection()
        self.assertTrue(self.test_db_path.exists())
        conn.close()

    def test_get_connection_returns_valid_connection(self):
        """Test get_connection returns a valid SQLite connection."""
        conn = sqlite_engine.get_connection()
        self.assertIsInstance(conn, sqlite3.Connection)

        # Test that we can execute a query
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        self.assertEqual(result[0], 1)
        conn.close()

    def test_insert_crawler_result_basic(self):
        """Test inserting a basic crawler result."""
        sqlite_engine.insert_crawler_result(
            storename="Kroger",
            weekly_ad_starting_date="2025-01-01",
            product="Bananas",
            image_url="http://example.com/banana.jpg",
            image_bytes=b"fake_image_data",
            price="0.59",
        )

        # Verify the data was inserted
        with sqlite3.connect(str(self.test_db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM crawler_results")
            result = cursor.fetchone()

        self.assertIsNotNone(result)
        self.assertEqual(result[1], "Kroger")  # storename
        self.assertEqual(result[2], "2025-01-01")  # weekly_ad_starting_date
        self.assertEqual(result[3], "Bananas")  # product
        self.assertEqual(result[4], "http://example.com/banana.jpg")  # image_url
        self.assertEqual(result[5], b"fake_image_data")  # image
        self.assertEqual(result[6], "0.59")  # price

    def test_insert_crawler_result_with_null_image(self):
        """Test inserting a crawler result with null image data."""
        sqlite_engine.insert_crawler_result(
            storename="HEB",
            weekly_ad_starting_date="2025-01-15",
            product="Apples",
            image_url=None,
            image_bytes=None,
            price="1.99",
        )

        with sqlite3.connect(str(self.test_db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM crawler_results WHERE product='Apples'")
            result = cursor.fetchone()

        self.assertIsNotNone(result)
        self.assertEqual(result[1], "HEB")
        self.assertIsNone(result[4])  # image_url
        self.assertIsNone(result[5])  # image

    def test_insert_multiple_crawler_results(self):
        """Test inserting multiple crawler results."""
        test_data = [
            ("Kroger", "2025-01-01", "Bananas", "url1", b"img1", "0.59"),
            ("HEB", "2025-01-08", "Apples", "url2", b"img2", "1.99"),
            ("TomThumb", "2025-01-15", "Oranges", "url3", b"img3", "2.49"),
        ]

        for data in test_data:
            sqlite_engine.insert_crawler_result(*data)

        with sqlite3.connect(str(self.test_db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM crawler_results")
            count = cursor.fetchone()[0]

        self.assertEqual(count, 3)

    def test_insert_crawler_result_with_large_image(self):
        """Test inserting a crawler result with large image data."""
        large_image = b"x" * (1024 * 1024)  # 1MB of data

        sqlite_engine.insert_crawler_result(
            storename="Store",
            weekly_ad_starting_date="2025-01-01",
            product="Product",
            image_url="url",
            image_bytes=large_image,
            price="9.99",
        )

        with sqlite3.connect(str(self.test_db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT image FROM crawler_results")
            result = cursor.fetchone()

        self.assertEqual(len(result[0]), 1024 * 1024)

    def test_insert_crawler_result_with_special_characters(self):
        """Test inserting a crawler result with special characters."""
        sqlite_engine.insert_crawler_result(
            storename='Store\'s & "Quotes"',
            weekly_ad_starting_date="2025-01-01",
            product="Product with 'special' chars: <>&",
            image_url="http://example.com/image?id=123&size=large",
            image_bytes=b"data",
            price="$9.99",
        )

        with sqlite3.connect(str(self.test_db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT storename, product, price FROM crawler_results")
            result = cursor.fetchone()

        self.assertEqual(result[0], 'Store\'s & "Quotes"')
        self.assertEqual(result[1], "Product with 'special' chars: <>&")
        self.assertEqual(result[2], "$9.99")

    def test_db_path_from_environment_variable(self):
        """Test DB_PATH can be set from environment variable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            custom_db_path = Path(tmpdir) / "custom.db"

            with patch.dict(os.environ, {"DB_PATH": str(custom_db_path)}):
                # Reload the module to pick up the environment variable
                import importlib

                importlib.reload(sqlite_engine)

                self.assertEqual(sqlite_engine.DB_PATH, custom_db_path)

    def test_auto_increment_id(self):
        """Test that id field auto-increments correctly."""
        for i in range(3):
            sqlite_engine.insert_crawler_result(
                storename=f"Store{i}",
                weekly_ad_starting_date="2025-01-01",
                product=f"Product{i}",
                image_url=None,
                image_bytes=None,
                price="1.00",
            )

        with sqlite3.connect(str(self.test_db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM crawler_results ORDER BY id")
            ids = [row[0] for row in cursor.fetchall()]

        self.assertEqual(ids, [1, 2, 3])


class TestDBPathConfiguration(unittest.TestCase):
    """Test cases for DB_PATH configuration logic."""

    def test_default_db_path_structure(self):
        """Test that default DB_PATH is correctly structured."""
        # This tests the actual module's DB_PATH when no env var is set
        with patch.dict(os.environ, {}, clear=True):
            if "DB_PATH" in os.environ:
                del os.environ["DB_PATH"]

            import importlib

            importlib.reload(sqlite_engine)

            db_path = sqlite_engine.DB_PATH
            self.assertIsInstance(db_path, Path)
            self.assertTrue(str(db_path).endswith("crawler_results.db"))
            self.assertIn("db_store", str(db_path))


if __name__ == "__main__":
    unittest.main()
