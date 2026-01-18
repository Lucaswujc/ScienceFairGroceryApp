"""Playwright-based scraper for H-E-B weekly ads."""

from urllib.parse import urljoin
import random
import time
import sys
import subprocess
import traceback
from typing import List, Tuple

from utility import download_image, save_grocery_items as save_to_json

try:
    from playwright.sync_api import (
        sync_playwright,
        TimeoutError as PlaywrightTimeoutError,
        Locator,
        Page,
    )
except Exception as exc:  # pragma: no cover - clearer installation guidance
    diag = []
    try:
        diag.append(f"sys.executable: {sys.executable}")
        try:
            pip_out = subprocess.check_output(
                [sys.executable, "-m", "pip", "show", "playwright"],
                stderr=subprocess.STDOUT,
                text=True,
            )
            diag.append("pip show playwright:\n" + pip_out.strip())
        except Exception as pip_exc:
            diag.append("pip show failed: " + str(pip_exc))
    except Exception:
        diag.append("failed to collect diagnostic info")

    diag.append(
        "import error: "
        + "".join(traceback.format_exception_only(type(exc), exc)).strip()
    )
    message = (
        "Playwright is required. Run 'pip install playwright' followed by "
        "'python -m playwright install'. Diagnostics:\n" + "\n".join(diag)
    )
    raise RuntimeError(message) from exc


def extract_heb_product(card: Locator) -> Tuple[str, str, str, bool]:
    """Extract product details from a single product card."""
    img = card.locator("img").first
    img_url = (img.get_attribute("src") or "").strip()
    item_name = (img.get_attribute("alt") or "").strip()

    title_spans = card.locator('[data-qe-id="productTitle"] span')
    for idx in range(title_spans.count()):
        text = (title_spans.nth(idx).inner_text() or "").strip()
        if text:
            item_name = text
            break

    price_text = ""
    price_elements = card.locator("xpath=.//*[contains(text(),'$')]")
    for idx in range(price_elements.count()):
        raw = (price_elements.nth(idx).inner_text() or "").strip()
        if "$" in raw and "/" not in raw:
            price_text = raw
            break

    unit_price = ""
    unit_price_elements = card.locator("xpath=.//*[contains(text(),' / ')]")
    for idx in range(unit_price_elements.count()):
        raw = (unit_price_elements.nth(idx).inner_text() or "").strip()
        if "$" in raw and "/" in raw:
            unit_price = raw
            break

    coupon_divs = card.locator(
        "xpath=.//*[contains(translate(text(),'COUPON','coupon'),'coupon')]"
    )
    has_coupon = coupon_divs.count() > 0

    buttons = card.locator("xpath=.//button")
    in_stock = False
    for idx in range(buttons.count()):
        if "Add to" in (buttons.nth(idx).inner_text() or ""):
            in_stock = True
            break

    full_price = f"{price_text} ({unit_price})" if unit_price else price_text
    if has_coupon:
        full_price += " [Coupon]"

    return item_name, img_url, full_price.strip(), in_stock


def scrape_page(page: Page) -> List[dict]:
    page.wait_for_selector('[data-component="product-card"]', timeout=20000)
    cards = page.locator('[data-component="product-card"]')
    count = cards.count()
    items = []
    for idx in range(count):
        card = cards.nth(idx)
        try:
            name, imageurl, price, stock = extract_heb_product(card)
        except Exception as exc:  # pragma: no cover - continue on extraction glitches
            print(f"Failed to parse card {idx}: {exc}")
            continue

        print("Product:", name)
        print("Image URL:", imageurl)
        print("Price:", price)
        print("In Stock:", stock)
        print("=" * 60)
        local_image_path, local_image_filename = download_image(imageurl, name, store="heb")
        items.append({"name": name, "image": local_image_filename, "price": price, "in_stock": stock, "image_url": imageurl})

    return items


def add_store_cookie(page: Page):
    page.context.add_cookies(
        [
            {
                "name": "SHOPPING_STORE_ID",
                "value": "796",
                "domain": ".heb.com",
                "path": "/",
                "secure": True,
                "httpOnly": False,
            }
        ]
    )


def main_flow(headless: bool = False, slow_mo: int = 0):
    base_url = "https://www.heb.com"
    weekly_ad_url = f"{base_url}/weekly-ad/deals"
    all_items: List[dict] = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=headless,
            slow_mo=slow_mo,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                " AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
            ),
            locale="en-US",
            viewport={"width": 1280, "height": 900},
        )

        page = context.new_page()
        page.goto(base_url, wait_until="domcontentloaded")
        add_store_cookie(page)
        page.goto(weekly_ad_url, wait_until="domcontentloaded")

        try:
            page.wait_for_selector('[data-component="product-card"]', timeout=20000)
        except PlaywrightTimeoutError:
            print("No product cards found on the H-E-B weekly ad page.")
            context.close()
            browser.close()
            return

        while True:
            all_items.extend(scrape_page(page))

            next_buttons = page.locator('[data-qe-id="paginationNext"]')
            if next_buttons.count() == 0:
                break

            next_button = next_buttons.first
            aria_disabled = next_button.get_attribute("aria-disabled")
            next_href = next_button.get_attribute("href")
            if aria_disabled == "true" or not next_href:
                break

            sleep_duration = random.uniform(1.5, 3.5)
            time.sleep(sleep_duration)  # Randomized delay before loading next page

            next_url = urljoin(base_url, next_href)
            page.goto(next_url, wait_until="domcontentloaded")

        try:
            context.close()
            browser.close()
        except Exception:
            pass

    save_to_json(all_items, "heb")


if __name__ == "__main__":
    main_flow(headless=False, slow_mo=0)
