#!/usr/bin/env python3
"""Automate Kroger flow with Playwright:
- open kroger.com
- click Weekly Ad navigation to land on /weeklyad
- wait for page load
- click 'View Other Ads' button (data-testid=ViewOtherAdsButton)
- in popup click a 'View Ad' button (data-testid starts with 'ViewAd-')
- wait for content and save a screenshot + print cookies

Usage:
  python kroger_flow.py --headful
  python kroger_flow.py --storage state.json  # reuse saved storage state
"""
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import argparse
import os
import time
from utility import download_image, save_grocery_items

HERE = os.path.dirname(__file__)
DEFAULT_URL = "https://www.kroger.com/"


def try_click(page, selectors, timeout=5000):
    for sel in selectors:
        try:
            locator = page.locator(sel)
            if locator.count() == 0:
                continue
            locator.first.click(timeout=timeout)
            return True
        except PlaywrightTimeoutError:
            continue
        except Exception:
            continue
    return False


def process_image_url(url: str) -> str:
    """Normalize Kroger CDN image URLs to a stable location and strip querystring."""
    if not url:
        return url
    S3_BASE_URL = "https://s3.us-west-1.wasabisys.com/kroger/Kroger/Montages/"
    KROGER_BASE_URL = "https://www.krogercdn.com/weeklyads/images/Kroger/Montages/"
    try:
        out = url.replace(KROGER_BASE_URL, S3_BASE_URL)
        clean = out.split("?", 1)[0]
        return clean
    except Exception:
        return url.split("?", 1)[0]


def _get_img_src_from_locator(img_locator):
    """Return best candidate image URL from a Playwright locator pointing to an <img>."""
    for attr in ("src", "data-src", "data-lazy-src", "data-original", "data-srcset", "srcset"):
        try:
            val = img_locator.get_attribute(attr)
            if not val:
                continue
            val = val.strip()
            if not val:
                continue
            # srcset or data-srcset: pick first URL before whitespace or comma
            if "srcset" in attr or ("," in val and " " in val):
                # split on comma first, then take first token and URL portion
                first = val.split(",")[0].strip()
                parts = first.split()
                return parts[0]
            return val
        except Exception:
            continue
    return ""


def extract_omni_deal_from_locator(card_locator):
    try:
        img_loc = card_locator.locator("img").first
        img_url = _get_img_src_from_locator(img_loc)
    except Exception:
        img_url = ""

    item_name = ""
    try:
        alt = img_loc.get_attribute("alt")
        if alt:
            item_name = alt.strip()
    except Exception:
        pass

    # try to get description text
    try:
        name_spans = card_locator.locator(".SWA-OmniDescriptionBlock .kds-Text--m")
        if name_spans.count() > 0:
            for i in range(name_spans.count()):
                t = name_spans.nth(i).inner_text().strip()
                if t:
                    item_name = t
                    break
    except Exception:
        pass

    promo_text = ""
    try:
        promo_divs = card_locator.locator(".SWA-OmniPricePrefix")
        if promo_divs.count() > 0:
            promo_text = promo_divs.first.inner_text().strip()
    except Exception:
        pass

    price_text = ""
    try:
        price_divs = card_locator.locator(".SWA-OmniPriceHeading")
        if price_divs.count() > 0:
            price_text = price_divs.first.get_attribute("aria-label") or price_divs.first.inner_text()
            price_text = (price_text or "").strip()
    except Exception:
        pass

    full_price = f"{promo_text} {price_text}".strip()
    return item_name, img_url, full_price


def extract_feature_deal_from_locator(card_locator):
    try:
        img_loc = card_locator.locator("img").first
        img_url = _get_img_src_from_locator(img_loc)
    except Exception:
        img_url = ""

    item_name = ""
    try:
        alt = img_loc.get_attribute("alt")
        if alt:
            item_name = alt.strip()
    except Exception:
        pass

    try:
        descs = card_locator.locator(".SWA-FeatureDealDescription")
        if descs.count() > 0:
            for i in range(descs.count()):
                t = descs.nth(i).inner_text().strip()
                if t:
                    item_name = t
                    break
    except Exception:
        pass

    item_price = ""
    try:
        price_div = card_locator.locator(".SWA-FeaturePriceHeading").first
        item_price = price_div.get_attribute("aria-label") or price_div.inner_text()
        item_price = (item_price or "").strip()
    except Exception:
        pass

    return item_name, img_url, item_price


def extract_and_save_items(page, store_name: str = "kroger"):
    """Find ad cards on the page, extract name/image/price, download images and save JSON."""
    cards = page.locator(".kds-Card")
    count = cards.count()
    print(f"Found {count} card(s) on the page — extracting...")
    items = []
    for i in range(count):
        card = cards.nth(i)
        class_attr = card.get_attribute("class") or ""
        name = image_url = price = None
        try:
            if "SWA-Omni" in class_attr:
                name, image_url, price = extract_omni_deal_from_locator(card)
            elif "SWA-Feature" in class_attr:
                name, image_url, price = extract_feature_deal_from_locator(card)
        except Exception:
            continue

        if not (name and image_url and price):
            continue

        new_image_url = process_image_url(image_url)
        local_img_full_path , local_img_file_name = download_image(new_image_url, name, store_name)
        if not local_img_full_path:
            continue

        item = {"name": name, "image": local_img_file_name, "price": price, "image_url": new_image_url}
        print("Extracted item:", item)

        items.append(item)

    if items:
        save_grocery_items(items, store_name)
    else:
        print("No items extracted to save.")


def run_flow(headful: bool, storage: str | None, screenshot_path: str | None, save_storage: str | None = None):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not headful)
        context_args = {}
        if storage:
            if os.path.exists(storage):
                context_args["storage_state"] = storage
        context = browser.new_context(**context_args)
        page = context.new_page()

        # 1) Land on kroger.com
        print("Navigating to kroger.com")
        page.goto(DEFAULT_URL, wait_until="load")
        time.sleep(1)

        # 2) Click Weekly Ad navigation — try common selectors robustly
        print("Trying to navigate to weekly ad page")
        weekly_selectors = [
            'a[href^="/weeklyad"]',
            'a:has-text("Weekly Ad")',
            'button:has-text("Weekly Ad")',
        ]
        clicked = try_click(page, weekly_selectors, timeout=5000)
        if not clicked:
            print("Could not find a direct weekly ad link/button. Attempting to open /weeklyad directly.")
            page.goto("https://www.kroger.com/weeklyad", wait_until="load")
        else:
            # wait for navigation
            try:
                page.wait_for_url("**/weeklyad**", timeout=10000)
            except PlaywrightTimeoutError:
                print("Timed out waiting for /weeklyad URL; continuing anyway.")

        # 3) Ensure we're on weeklyad and fully loaded
        print("Waiting for weekly ad page to load")
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except PlaywrightTimeoutError:
            print("Network idle wait timed out; proceeding after short sleep.")
            time.sleep(2)

        # 4) Click 'View Other Ads' button by data-testid
        print("Locating 'View Other Ads' button")
        try:
            view_other = page.locator('[data-testid="ViewOtherAdsButton"]')
            view_other.first.wait_for(state="visible", timeout=8000)
            view_other.first.click()
        except Exception:
            print("Failed to click View Other Ads by data-testid — trying text fallback")
            try_click(page, ['button:has-text("View Other Ads")', 'text=View Other Ads'], timeout=5000)

        # 5) In the popup, click a View Ad button whose data-testid starts with 'ViewAd-'
        print("Waiting for View Ad entries in popup")
        try:
            ad_button = page.locator('[data-testid^="ViewAd-"]')
            ad_button.first.wait_for(state="visible", timeout=10000)
            ad_button.first.click()
        except Exception:
            print("Could not find a ViewAd button with data-testid^=ViewAd-. Trying alternative selectors.")
            try_click(page, ['button[aria-label^="View Ad"]', 'button:has-text("View Ad")'], timeout=7000)

        # 6) Wait for ad content to load — use networkidle + small sleep
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except PlaywrightTimeoutError:
            print("Network idle timeout after clicking View Ad; continuing after brief delay.")
        time.sleep(2)

        # 6.5) Extract card items (images, names, prices) and save
        try:
            extract_and_save_items(page)
        except Exception as e:
            print("Failed to extract and save items:", e)

        # 7) Capture final state: URL, cookies, screenshot
        print("Final URL:", page.url)
        try:
            cookies = context.cookies()
            print("Cookies:")
            for c in cookies:
                print(c)
        except Exception as e:
            print("Failed to read cookies:", e)

        # Optionally save full Playwright storage state (cookies + localStorage)
        if save_storage:
            try:
                context.storage_state(path=save_storage)
                print("Saved Playwright storage state to:", save_storage)
            except Exception as e:
                print("Failed to save storage state:", e)

        try:
            if screenshot_path:
                page.screenshot(path=screenshot_path, full_page=True)
                print("Saved screenshot to:", screenshot_path)
        except Exception as e:
            print("Screenshot failed:", e)

        input("Review the browser, then press Enter to close it...")
        browser.close()


def main():
    ap = argparse.ArgumentParser(description="Kroger weekly ad Playwright flow")
    ap.add_argument("--headful", action="store_true", help="Run browser visible (recommended for debugging)")
    ap.add_argument("--storage", default=None, help="Path to Playwright storage state JSON to reuse session")
    ap.add_argument("--screenshot", default=os.path.join(HERE, "kroger_ad.png"))
    ap.add_argument("--save-storage", default=None, help="Path to write Playwright storage state (cookies+localStorage)")
    args = ap.parse_args()

    # run_flow(headful=args.headful, storage=args.storage, 
    #          screenshot_path=args.screenshot, 
    #          save_storage=args.save_storage)
    run_flow(headful= True, storage="state.json", 
             screenshot_path=None, 
             save_storage=None)


if __name__ == "__main__":
    main()
