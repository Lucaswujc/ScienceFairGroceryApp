#!/usr/bin/env python3
"""Save and reuse Playwright storage state for interactive sessions.

Usage:
  python playwright_state.py --action save   # open headful browser, interact, then save state.json
  python playwright_state.py --action reuse  # launch browser with saved state.json and open target URL

This script is intentionally simple: it opens a headful browser so you can
manually solve CAPTCHAs / login, then saves `state.json`. Reuse mode loads
that state to land directly on the target page.
"""
from playwright.sync_api import sync_playwright
import argparse
import os

HERE = os.path.dirname(__file__)
STATE_FILE = os.path.join(HERE, "state.json")
DEFAULT_URL = "https://www.kroger.com/weeklyad/"


def save_state(url: str):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto(url)
        print(f"Opened {url} in headful browser.")
        input(f"Interact with the page (login/CAPTCHA). Press Enter to save state to {STATE_FILE}...")
        context.storage_state(path=STATE_FILE)
        print("Saved storage state to:", STATE_FILE)
        browser.close()


def reuse_state(url: str):
    if not os.path.exists(STATE_FILE):
        print("No state file found at:", STATE_FILE)
        print("Run with --action save first to create it.")
        return
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(storage_state=STATE_FILE)
        page = context.new_page()
        page.goto(url)
        print("Loaded page with saved state. Current cookies:")
        for c in context.cookies():
            print(c)
        screenshot = os.path.join(HERE, "reused.png")
        page.screenshot(path=screenshot, full_page=True)
        print("Saved screenshot to:", screenshot)
        input("Press Enter to close browser...")
        browser.close()


def launch_persistent(url: str, user_data_dir: str):
    # Alternative approach: persistent context keeps full profile (cookies, localStorage, extensions)
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(user_data_dir=user_data_dir, headless=False)
        page = context.new_page()
        page.goto(url)
        print(f"Launched persistent context with user data dir: {user_data_dir}")
        input("Interact, then press Enter to exit persistent session...")
        context.close()


def main():
    ap = argparse.ArgumentParser(description="Playwright save/reuse storage state helper")
    ap.add_argument("--action", choices=["save", "reuse", "persistent"], required=True)
    ap.add_argument("--url", default=DEFAULT_URL)
    ap.add_argument("--user-data-dir", default=None, help="Path for persistent context (optional)")
    args = ap.parse_args()

    if args.action == "save":
        save_state(args.url)
    elif args.action == "reuse":
        reuse_state(args.url)
    elif args.action == "persistent":
        if not args.user_data_dir:
            print("--user-data-dir is required for persistent mode")
            return
        launch_persistent(args.url, args.user_data_dir)


if __name__ == "__main__":
    main()
