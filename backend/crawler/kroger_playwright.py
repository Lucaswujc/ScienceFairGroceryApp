"""Playwright-based Kroger weekly ad scraper.

Implements:
- process_image_url(url)
- extract_omni_deal(card)
- extract_feature_deal(card)
- main_flow(headless=False, slow_mo=0)

Usage:
    pip install playwright
    python -m playwright install
    python backend/crawler/kroger_playwright.py
"""
from urllib.parse import urljoin
import random
import time
from typing import Tuple, List

from utility import save_grocery_items as save_to_json, download_image

import sys
import subprocess
import traceback

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
except Exception as exc:  # pragma: no cover - helpful error
    diag = []
    try:
        diag.append(f"sys.executable: {sys.executable}")
        try:
            pip_out = subprocess.check_output([sys.executable, "-m", "pip", "show", "playwright"], stderr=subprocess.STDOUT, text=True)
            diag.append("pip show playwright:\n" + pip_out.strip())
        except Exception as e:
            diag.append("pip show failed: " + str(e))
    except Exception:
        diag.append("failed to collect diagnostic info")

    diag.append("import error: " + "".join(traceback.format_exception_only(type(exc), exc)).strip())
    message = (
        "Playwright is required. Run: 'pip install playwright' and then 'python -m playwright install'. "
        "Diagnostics:\n" + "\n".join(diag)
    )
    raise RuntimeError(message) from exc


KROGER_S3_BASE = "https://s3.us-west-1.wasabisys.com/kroger/Kroger/Montages/"
KROGER_CDN_BASE = "https://www.krogercdn.com/weeklyads/images/Kroger/Montages/"

def dismiss_modal(page):
    selectors = [
        'button[aria-label="Close"]',
        'button[title="Close"]',
        'button:has-text("No Thanks")',
        'button:has-text("No, thanks")',
        '.modal button.close',
        '[data-testid*="close"]',
    ]
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            if loc.count() and loc.is_visible():
                loc.click(timeout=2000)
                return True
        except Exception:
            pass
    # fallbacks
    try:
        page.keyboard.press("Escape")
    except Exception:
        pass
    # aggressive DOM removal fallback
    page.evaluate("""() => {
        const m = document.querySelector('.react-modal, .modal, [data-modal], #modal');
        if (m) m.remove();
        document.body.style.overflow = '';
    }""")
    return True

def process_image_url(url: str) -> str:
    """Normalize Kroger montage image URLs to use S3 base and remove query params."""
    if not url:
        return url
    url = url.replace(KROGER_CDN_BASE, KROGER_S3_BASE)
    clean_url = url.split("?", 1)[0]
    return clean_url


def extract_omni_deal(card) -> Tuple[str, str, str]:
    """Extract name, img_url, and price for an Omni card (Playwright Locator)."""
    img = card.locator("img").first
    img_url = img.get_attribute("src") or ""
    item_name = (img.get_attribute("alt") or "").strip()

    # Description may exist in the specified selector
    title_spans = card.locator(".SWA-OmniDescriptionBlock .kds-Text--m")
    for i in range(title_spans.count()):
        t = (title_spans.nth(i).inner_text() or "").strip()
        if t:
            item_name = t
            break

    # Promo prefix
    promo_text = ""
    promo_divs = card.locator(".SWA-OmniPricePrefix")
    if promo_divs.count() > 0:
        promo_text = (promo_divs.nth(0).inner_text() or "").strip()

    price_text = ""
    price_divs = card.locator(".SWA-OmniPriceHeading")
    if price_divs.count() > 0:
        price_text = price_divs.nth(0).get_attribute("aria-label") or ""
        price_text = price_text.strip()

    full_price = f"{promo_text} {price_text}".strip()

    return item_name or "", img_url or "", full_price


def extract_feature_deal(card) -> Tuple[str, str, str]:
    """Extract name, img_url, and price for a Feature card (Playwright Locator)."""
    img = card.locator("img").first
    img_url = img.get_attribute("src") or ""
    item_name = (img.get_attribute("alt") or "").strip()

    name_spans = card.locator(".SWA-FeatureDealDescription")
    for i in range(name_spans.count()):
        t = (name_spans.nth(i).inner_text() or "").strip()
        if t:
            item_name = t
            break

    price_div = card.locator(".SWA-FeaturePriceHeading").first
    item_price = price_div.get_attribute("aria-label") or ""

    return item_name or "", img_url or "", item_price.strip()


def main_flow(headless: bool = False, slow_mo: int = 0):
    """Main scraping flow using Playwright for Kroger weekly ad.

    headless: run without opening a window when True
    slow_mo: ms to slow down Playwright actions (helpful for debugging)
    """
    base_url = "https://www.kroger.com/weeklyad"
    items_all: List[dict] = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=headless, slow_mo=slow_mo, args=["--disable-blink-features=AutomationControlled"])
        context = browser.new_context(
            user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                        " (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
            locale="en-US",
            viewport={"width": 1280, "height": 900},
        )

        page = context.new_page()
        page.goto(base_url)
        dismiss_modal(page)
        time.sleep(random.uniform(2, 4))
        
        try:
            page.wait_for_selector(".kds-Card", timeout=20000)
        except PlaywrightTimeoutError:
            print("No cards found on Kroger weekly ad page.")
            context.close()
            browser.close()
            return

        time.sleep(random.uniform(1.5, 3.0))

        cards = page.locator(".kds-Card")
        count = cards.count()

        for i in range(count):
            card = cards.nth(i)
            try:
                class_attr = card.get_attribute("class") or ""
            except Exception:
                class_attr = ""

            name = image_url = price = None
            if "SWA-Omni" in class_attr:
                name, image_url, price = extract_omni_deal(card)
            elif "SWA-Feature" in class_attr:
                name, image_url, price = extract_feature_deal(card)

            if not (name and image_url and price):
                continue

            new_image_url = process_image_url(image_url)
            local_img_path = None
            if new_image_url:
                try:
                    local_img_path = download_image(new_image_url, name, "kroger")
                except Exception:
                    local_img_path = None

            if not local_img_path:
                continue

            print("Product:", name)
            print("Image URL:", image_url)
            print("Price:", price)
            item = {"name": name, "image": local_img_path, "price": price}
            items_all.append(item)
            print("=" * 60)

        try:
            context.close()
            browser.close()
        except Exception:
            pass

    save_to_json(items_all, "kroger")


if __name__ == "__main__":
    main_flow(headless=False, slow_mo=0)
