import os
import re
import json
import random
import urllib.request
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium import webdriver
from datetime import date

from crawler.crawler_configs import FILE_SYSTEM_CONFIG


def get_store_week_folder(storename: str, week: str, create_if_not_exists: bool = True):
    """
    Generate standardized folder path for a store's weekly data.
    Structure: BASE_DIR/storename/weekstartdate/

    This folder will contain:
    - JSON file with grocery items
    - Image files for that week's items

    Args:
        storename (str): Name of the store (e.g., "kroger", "heb").
        week (str): Week in YYYY-Www format (e.g., "2024-W52").
        create_if_not_exists (bool): If True, creates the folder if it doesn't exist.

    Returns:
        str: Absolute path to the store/week folder.
    """
    base_dir = FILE_SYSTEM_CONFIG.get(
        "DATA_BASE_DIR", os.path.join(os.path.dirname(__file__), "grocery_data")
    )
    store_week_folder = os.path.join(base_dir, storename, week)

    if create_if_not_exists and not os.path.exists(store_week_folder):
        os.makedirs(store_week_folder, exist_ok=True)

    return store_week_folder


def get_json_file_path(storename: str, week: str):
    """
    Get the JSON file path for storing grocery items.

    Args:
        storename (str): Name of the store.
        week (str): Week in YYYY-Www format.

    Returns:
        str: Absolute path to the JSON file.
    """
    folder = get_store_week_folder(storename, week)
    return os.path.join(folder, "weekly_ad.json")


def download_image(url, name, store, week=None):
    """
    Download an image and save it to the store/week folder.

    Args:
        url (str): URL of the image to download.
        name (str): Name/description of the item.
        store (str): Store name (e.g., "kroger", "heb").
        week (str, optional): Week in YYYY-Www format. If None, uses current week.

    Returns:
        str: Local path where the image was saved, or None if download failed.
    """
    # Get current week if not provided
    if week is None:
        week = date.today().strftime("%Y-W%U")

    # Get the folder for this store/week
    folder_path = get_store_week_folder(store, week)

    # Sanitize filename
    filename = re.sub(r"[^\w\-_\.]", "_", name.replace(" ", ""))[:50]

    # Get file extension (before any query parameters)
    ext = os.path.splitext(url)[-1].split("?")[0]
    if not ext or len(ext) > 5:
        ext = ".jpg"  # Fallback extension if unknown

    local_path = os.path.join(folder_path, f"{filename}{ext}")

    # Download image using urlopen
    try:
        with (
            urllib.request.urlopen(url) as response,
            open(local_path, "wb") as out_file,
        ):
            out_file.write(response.read())
        return local_path
    except Exception as e:
        print(f"Failed to download image for {name}: {e}")
        return None


def save_grocery_items(data, storename, week=None):
    """
    Save a list of grocery items to a JSON file in the store/week folder.

    Args:
        data (list): List of dictionaries containing grocery item data.
        storename (str): Name of the store (e.g., "kroger", "heb").
        week (str, optional): Week in YYYY-Www format. If None, uses current week.

    Raises:
        ValueError: If data is not a list of dictionaries.
    """
    # Validate input data
    if not isinstance(data, list) or not all(isinstance(d, dict) for d in data):
        raise ValueError("Data must be a list of dictionaries.")

    # Get current week if not provided
    if week is None:
        week = date.today().strftime("%Y-W%U")

    # Get the JSON file path
    file_path = get_json_file_path(storename, week)

    # Load existing content if the file exists
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            try:
                existing_data = json.load(f)
                if not isinstance(existing_data, list):
                    existing_data = []
            except json.JSONDecodeError:
                existing_data = []
    else:
        existing_data = []

    # Append new data and write back to file
    existing_data.extend(data)

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(existing_data, f, indent=4)

    print(f"Data saved to {file_path}")


def get_stealth_driver(
    chrome_path=FILE_SYSTEM_CONFIG["chrome_path"],
    driver_path=FILE_SYSTEM_CONFIG["chromedriver_path"],
):
    chrome_options = Options()
    chrome_options.binary_location = chrome_path

    # Set a random, realistic user-agent
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    ]
    chrome_options.add_argument(f"user-agent={random.choice(user_agents)}")

    # Anti-bot evasion flags
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)

    # Headless mode (optional – bots are more detectable headless)
    # chrome_options.add_argument("--headless")

    # Avoid webdriver property detection
    chrome_prefs = {
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False,
    }
    chrome_options.add_experimental_option("prefs", chrome_prefs)

    # Launch driver
    service = Service(driver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)

    # Remove `navigator.webdriver` flag via DevTools
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {
            "source": """
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
        """
        },
    )

    return driver


def get_store_ads(storename: str, week: str) -> list:
    """
    Retrieve weekly ad for a store for a particular week from a JSON file.
    Loads images as binary byte arrays from the stored image files.

    Args:
        storename (str): Name of the store (e.g., "kroger", "heb").
        week (str): Week in YYYY-Www format (e.g., "2024-W52").

    Returns:
        list: List of dictionaries with product name, price, and image (as binary bytes).
              Format: [{"name": str, "price": str, "image": bytes}, ...]

    Raises:
        FileNotFoundError: If no weekly ad file is found for the store and week.
    """
    import base64

    file_path = get_json_file_path(storename, week)

    if not os.path.isfile(file_path):
        raise FileNotFoundError(
            f"No weekly ad file found for store '{storename}' and week '{week}' at {file_path}"
        )

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # # Load images as binary byte arrays
    # result = []
    # for item in data:
    #     image_path = item.get("image")
    #     image_base64 = None

    #     if image_path and os.path.isfile(image_path):
    #         try:
    #             with open(image_path, "rb") as img_file:
    #                 image_bytes = img_file.read()
    #                 image_base64 = (
    #                     base64.b64encode(image_bytes).decode() if image_bytes else None
    #                 )
    #         except Exception as e:
    #             print(f"Warning: Failed to load image {image_path}: {e}")

    #     result.append(
    #         {
    #             "name": item.get("name"),
    #             "price": item.get("price"),
    #             "image": image_base64,
    #         }
    #     )

    return data
