import os
import sqlite3
from pathlib import Path

# Determine DB path from environment variable or default location
DB_PATH = os.environ.get("DB_PATH")
if not DB_PATH:
    project_root = Path(__file__).resolve().parents[1]
    db_dir = project_root / "db_store"
    db_dir.mkdir(exist_ok=True)
    DB_PATH = db_dir / "crawler_results.db"
else:
    DB_PATH = Path(DB_PATH)


def db_exists():
    return Path(str(DB_PATH)).is_file()


def get_connection():
    if not db_exists():
        init_db()
    return sqlite3.connect(str(DB_PATH))


def init_db():
    # Open a direct connection to avoid recursion
    with sqlite3.connect(str(DB_PATH)) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS crawler_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                storename TEXT NOT NULL,
                weekly_ad_starting_date TEXT NOT NULL,
                product TEXT NOT NULL,
                image_url TEXT,
                image BLOB,
                price TEXT NOT NULL
            )
        """)
        conn.commit()


def insert_crawler_result(
    storename, weekly_ad_starting_date, product, image_url, image_bytes, price
):
    """
    Insert a new crawler result into the database.
    image_bytes should be raw image data (not base64-encoded).
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO crawler_results (storename, weekly_ad_starting_date, product, image_url, image, price)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                storename,
                weekly_ad_starting_date,
                product,
                image_url,
                image_bytes,
                price,
            ),
        )
        conn.commit()


# Remove the main method and ensure this module is only used as an importable utility.
# The get_connection() function will handle DB creation if needed.

# Example usage:
# from db_engine.sqlite_engine import insert_crawler_result
#
# with open('path_to_image.jpg', 'rb') as img_file:
#     image_bytes = img_file.read()
#
# insert_crawler_result(
#     storename="Kroger",
#     weekly_ad_starting_date="2025-09-01",
#     product="Bananas",
#     image_bytes=image_bytes,
#     price=0.59
# )
