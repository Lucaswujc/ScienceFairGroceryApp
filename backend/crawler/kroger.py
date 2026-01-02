import random
import time
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from utility import save_grocery_items as save_to_json
from utility import download_image
from utility import get_stealth_driver
from crawler_configs import FILE_SYSTEM_CONFIG


def process_image_url(url: str) -> str:
    S3_BASE_URL = "https://s3.us-west-1.wasabisys.com/kroger/Kroger/Montages/"
    KROGER_BASE_URL = "https://www.krogercdn.com/weeklyads/images/Kroger/Montages/"
    url = url.replace(KROGER_BASE_URL, S3_BASE_URL)
    clean_url = url.split("?", 1)[0]
    return clean_url


def extract_omni_deal(card):
    img = card.find_element(By.TAG_NAME, "img")
    img_url = img.get_attribute("src")
    item_name = img.get_attribute("alt").strip()

    name_spans = card.find_elements(
        By.CSS_SELECTOR, ".SWA-OmniDescriptionBlock .kds-Text--m"
    )
    for span in name_spans:
        if span.text.strip():
            item_name = span.text.strip()
            break

    # Check for promo prefix like "Buy 2 Get 3"
    promo_text = ""
    promo_divs = card.find_elements(By.CLASS_NAME, "SWA-OmniPricePrefix")
    if promo_divs:
        promo_text = promo_divs[0].text.strip()

    price_text = ""
    price_divs = card.find_elements(By.CLASS_NAME, "SWA-OmniPriceHeading")
    if price_divs:
        price_text = price_divs[0].get_attribute("aria-label").strip()

    # Combine promo + price, or just show promo if price is empty (e.g., "FREE")
    full_price = f"{promo_text} {price_text}".strip()

    return item_name, img_url, full_price


def extract_feature_deal(card):
    img = card.find_element(By.TAG_NAME, "img")
    img_url = img.get_attribute("src")
    item_name = img.get_attribute("alt").strip()

    name_spans = card.find_elements(By.CLASS_NAME, "SWA-FeatureDealDescription")
    for span in name_spans:
        if span.text.strip():
            item_name = span.text.strip()
            break

    price_div = card.find_element(By.CLASS_NAME, "SWA-FeaturePriceHeading")
    item_price = price_div.get_attribute("aria-label").strip()

    return item_name, img_url, item_price


def main_flow():
    chrome_options = Options()
    chrome_options.binary_location = FILE_SYSTEM_CONFIG["chrome_path"]
    chrome_lib_path = FILE_SYSTEM_CONFIG["chromedriver_path"]

    driver = get_stealth_driver(chrome_options.binary_location, chrome_lib_path)

    driver.get("https://www.kroger.com/weeklyad/weeklyad")
    WebDriverWait(driver, 20).until(
        EC.presence_of_all_elements_located((By.CLASS_NAME, "kds-Card"))
    )
    time.sleep(random.uniform(2, 4))

    cards = driver.find_elements(By.CLASS_NAME, "kds-Card")
    items = []
    for card in cards:
        class_attr = card.get_attribute("class")
        name = image_url = price = None
        if class_attr:
            if "SWA-Omni" in class_attr:
                name, image_url, price = extract_omni_deal(card)
            elif "SWA-Feature" in class_attr:
                name, image_url, price = extract_feature_deal(card)
        if not (name and image_url and price):
            continue
        new_image_url = process_image_url(image)
        local_img_path = download_image(new_image_url, name, "kroger")
        if not local_img_path:
            continue  # skip this item if image download failed
        print("Product:", name)
        print("Image URL:", image_url)
        print("Price:", price)
        item = {"name": name, "image": local_img_path, "price": price}
        items.append(item)
        print("=" * 60)
    save_to_json(items, "kroger")
    driver.quit()


if __name__ == "__main__":
    main_flow()
    exit()
