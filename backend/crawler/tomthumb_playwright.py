import base64
from playwright.sync_api import sync_playwright
import json
import re
import os
import time
import random
from utility import download_image, get_store_week_folder, save_grocery_items

def _parse_price_from_text(text: str) -> str:
    """Return first price found like $1.23 or empty string."""
    if not text:
        return ""
    m = re.search(r"\$\s*\d{1,3}(?:[\,\d]*)(?:\.\d{1,2})?", text)
    if m:
        return m.group(0).replace(" ", "")
    return ""


def _load_cookies_from_file(context, file_path: str = "tomthumb_state.json"):
    """Load cookies from a JSON file into the Playwright context."""
    try:
        with open(file_path, "r") as f:
            cookies = json.load(f)
        
        # Playwright expects cookies in a specific format
        formatted_cookies = []
        for cookie in cookies:
            formatted_cookie = {
                "name": cookie.get("name"),
                "value": cookie.get("value"),
                "domain": cookie.get("domain"),
                "path": cookie.get("path", "/"),
                "secure": cookie.get("secure", False),
                "httpOnly": cookie.get("httpOnly", False),
                "sameSite": "Strict" if cookie.get("sameSite") == "strict" else ("Lax" if cookie.get("sameSite") == "lax" else "None"),
            }
            if cookie.get("expirationDate"):
                formatted_cookie["expires"] = cookie.get("expirationDate")
            
            formatted_cookies.append(formatted_cookie)
        
        context.add_cookies(formatted_cookies)
        print(f"[info] Loaded {len(formatted_cookies)} cookies from {file_path}")
    except FileNotFoundError:
        print(f"[warning] Cookie file {file_path} not found, continuing without cookies")
    except Exception as e:
        print(f"[warning] Error loading cookies: {e}")

def _click_buttons_and_capture_sidepanel_images(page, frame, timeout: int = 3000) -> dict:
    """Click each overlay button inside the main frame, open the aside panel,
    find `.single-media-container img`, download the image, and return a map
    of item_id -> {image: local_path_or_url, alt: alt_text, name: label}.
    """
    results = {}
    try:
        btns = frame.locator("button[data-product-id]")
        total = 0
        try:
            total = btns.count()
        except Exception:
            total = 0
        flyer_groups = {}
        try:
            flyers = frame.locator("sfml-flyer-image")
            num_flyers = flyers.count()
            print(f"[info] Found {num_flyers} flyers")
            
            for flyer_idx in range(num_flyers):
                flyer = flyers.nth(flyer_idx)
                try:
                    flyer_id = flyer.evaluate("el => el.getAttribute('sfml-anchor-id') || el.getAttribute('id') || `flyer-${Math.random().toString(36).substr(2, 9)}`")
                except Exception:
                    flyer_id = f"flyer-{flyer_idx}"
                
                # Find all buttons within this specific flyer
                btns_in_flyer = flyer.locator("button[data-product-id]")
                try:
                    count = btns_in_flyer.count()
                except Exception:
                    count = 0
                
                # Map button indices in the main frame to this flyer
                indices_in_flyer = []
                for btn_idx in range(total):
                    btn = btns.nth(btn_idx)
                    try:
                        # Check if this button's closest sfml-flyer-image matches current flyer
                        belongs_to_flyer = btn.evaluate(f"""el => {{
                            const flyer = el.closest('sfml-flyer-image');
                            const currentFlyer = document.querySelectorAll('sfml-flyer-image')[{flyer_idx}];
                            return flyer === currentFlyer;
                        }}""")
                        if belongs_to_flyer:
                            indices_in_flyer.append(btn_idx)
                    except Exception:
                        pass
                
                if indices_in_flyer:
                    flyer_groups[flyer_id] = indices_in_flyer
                    print(f"Flyer '{flyer_id}': {len(indices_in_flyer)} buttons at indices {indices_in_flyer}")
        except Exception as e:
            print(f"[debug] Error grouping by sfml-flyer-image: {e}")
            flyer_groups = {'ungrouped': list(range(total))}
        
        # Randomize each flyer's button order and iterate
        flyer_keys = list(flyer_groups.keys())
        random.shuffle(flyer_keys)
        
        for flyer_id in flyer_keys:
            indices = flyer_groups[flyer_id]
            random.shuffle(indices)  # Random button order within this flyer
            
            print(f"\n[info] Processing flyer '{flyer_id}' with randomized indices: {indices}")
            
            for i in indices:
                node = btns.nth(i)
                try:
                    item_id = node.get_attribute("data-product-id") or node.get_attribute("data-global-id") or f"btn-{i}"
                    name = node.get_attribute("aria-label") or node.get_attribute("label") or ""
                    price = _parse_price_from_text(name)
                except Exception:
                    item_id = f"btn-{i}"
                    name = ""
                    price = ""

                img_local = ""
                alt = ""
                clicked = False
                try:
                    node.scroll_into_view_if_needed()
                    node.click(timeout=2000)
                    clicked = True
                except Exception:
                    try:
                        node.evaluate("el => el.click()")
                        clicked = True
                    except Exception:
                        clicked = False

                if clicked:
                    try:
                        # wait for aside iframe to attach
                        el = page.wait_for_selector("iframe.asideframe", timeout=timeout)
                        aside_frame = el.content_frame()
                        if aside_frame:
                            img_el = aside_frame.query_selector(".single-media-container img")
                            if img_el:
                                src = img_el.get_attribute("src") or img_el.get_attribute("data-src") or img_el.get_attribute("data-srcset") or ""
                                alt = img_el.get_attribute("alt") or ""
                                if src and "," in src:
                                    src = src.split(",")[0].strip().split(" ")[0]
                                print(alt + " " + src)
                                # try to download remote image
                                try:
                                    local = None
                                    if src and src.startswith("data:"):
                                        # inline data URL - write directly
                                        header, b64 = src.split(",", 1)
                                        folder = get_store_week_folder("tomthumb")
                                        fname = f"{item_id}.jpg"
                                        path = os.path.join(folder, fname)
                                        with open(path, "wb") as f:
                                            f.write(base64.b64decode(b64))
                                        local_img_full_path, local_imag_file_name  = path, fname
                                    elif src:
                                        local_img_full_path, local_imag_file_name = download_image(src, name or item_id, "tomthumb")

                                    if local_img_full_path:
                                        img_local = local_imag_file_name
                                    else:
                                        img_local = src or ""
                                except Exception as e:
                                    print(f"[debug] failed to download side panel image for {item_id}: {e}")
                        
                    except Exception:
                        # nothing found in side panel
                        img_local = ""
                        alt = ""

                results[item_id] = {"image": img_local or "", "alt": alt, "name": name, "price": price}
                # random sleep to avoid being too fast (random < 3s)
                time.sleep(random.uniform(1, 3))
    except Exception as e:
        print(f"[debug] _click_buttons_and_capture_sidepanel_images error: {e}")
    return results


def extract_tom_thumb_products():

    import os

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                        " (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
            locale="en-US",
            viewport={"width": 1280, "height": 800},
            java_script_enabled=True,
        )
        # Load cookies before navigating
        _load_cookies_from_file(context, "crawler/tomthumb_state.json")
        
        page = context.new_page()
        
        # Navigate to Tom Thumb weekly ad
        page.goto("https://www.tomthumb.com/weeklyad", wait_until="load")
        
        # Add slight delay for page to fully render
        time.sleep(random.uniform(2, 4))
        
        # wait for the iframe to appear
        iframe_el = page.wait_for_selector("iframe.mainframe", timeout=20000)

        # frame reference for the main iframe where the content is rendered
        frame = iframe_el.content_frame()
        
        # Click buttons to open side panel images and download them
        results = _click_buttons_and_capture_sidepanel_images(page, frame, timeout=3000)

        
        print(f"Found {len(results)} products")
        print(json.dumps(results, indent=2))
        
        # Save results to JSON using utility function
        data_to_save = [{"name": v.get("name"), "price": v.get("price"), "image": v.get("image")} for v in results.values()]
        save_grocery_items(data_to_save, "tomthumb")
        
        try:
            context.close()
            browser.close()
        except Exception:
            pass
        return results

# Run the script
if __name__ == "__main__":
    extract_tom_thumb_products()