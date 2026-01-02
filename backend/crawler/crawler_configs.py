
from pathlib import Path
import sys
import shutil

# Derive base paths relative to this file so configuration works across machines
BASE_DIR = Path(__file__).resolve().parent  # backend/crawler
ROOT_DIR = BASE_DIR.parent  # backend
LIB_DIR = ROOT_DIR / "Lib"

# Platform-aware executable suffix
exe_suffix = ".exe" if sys.platform.startswith("win") else ""

# Local bundled candidates
chrome_local = LIB_DIR / "chrome-win64" / f"chrome{exe_suffix}"
chromedriver_local = LIB_DIR / "chromedriver-win64" / f"chromedriver{exe_suffix}"

# System fallbacks (search common names)
chrome_candidates = [
    "google-chrome",
    "chrome",
    "chromium",
    "chromium-browser",
]
chrome_system = next((shutil.which(name) for name in chrome_candidates if shutil.which(name)), None)
chromedriver_system = shutil.which("chromedriver")

# Final chosen paths (prefer local bundle when present)
chrome_path = str(chrome_local) if chrome_local.exists() else (chrome_system or "")
chromedriver_path = str(chromedriver_local) if chromedriver_local.exists() else (chromedriver_system or "")

FILE_SYSTEM_CONFIG = {
    "DATA_BASE_DIR": str(BASE_DIR / "grocery_data"),
    # Legacy paths - deprecated, kept for backward compatibility
    "IMAGES_BASE_DIR": str(BASE_DIR / "grocery_images"),
    "ITEMS_BASE_DIR": str(BASE_DIR / "grocery_items"),
    "S3_BASE_URL": "https://s3.us-west-1.wasabisys.com/kroger/Kroger/Montages/",
    "KROGER_BASE_URL": "https://www.krogercdn.com/weeklyads/images/Kroger/Montages/",
    "chrome_path": chrome_path,
    "chromedriver_path": chromedriver_path,
}
