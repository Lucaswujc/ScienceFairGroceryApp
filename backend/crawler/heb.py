from utility import save_grocery_items as save_to_json
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium import webdriver
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import urljoin


def extract_heb_product(card):
    img = card.find_element(By.TAG_NAME, "img")
    img_url = img.get_attribute("src")
    item_name = img.get_attribute("alt").strip()

    name_spans = card.find_elements(By.CSS_SELECTOR, '[data-qe-id="productTitle"] span')
    for span in name_spans:
        if span.text.strip():
            item_name = span.text.strip()
            break

    price_text = ""
    price_elements = card.find_elements(By.XPATH, ".//*[contains(text(),'$')]")
    for elem in price_elements:
        text = elem.text.strip()
        if "$" in text and "/" not in text:
            price_text = text
            break

    unit_price = ""
    unit_price_elements = card.find_elements(By.XPATH, ".//*[contains(text(),' / ')]")
    for elem in unit_price_elements:
        text = elem.text.strip()
        if "$" in text and "/" in text:
            unit_price = text
            break

    coupon_divs = card.find_elements(
        By.XPATH, ".//*[contains(translate(text(),'COUPON','coupon'),'coupon')]"
    )
    has_coupon = bool(coupon_divs)

    buttons = card.find_elements(By.XPATH, ".//button")
    in_stock = any("Add to" in btn.text for btn in buttons)

    full_price = f"{price_text} ({unit_price})" if unit_price else price_text
    if has_coupon:
        full_price += " [Coupon]"

    return item_name, img_url, full_price.strip(), in_stock


def scrape_page(driver):
    WebDriverWait(driver, 20).until(
        EC.presence_of_all_elements_located(
            (By.CSS_SELECTOR, '[data-component="product-card"]')
        )
    )

    cards = driver.find_elements(By.CSS_SELECTOR, '[data-component="product-card"]')
    items = []
    for card in cards:
        name, image, price, stock = extract_heb_product(card)
        print("Product:", name)
        print("Image URL:", image)
        print("Price:", price)
        print("In Stock:", stock)
        print("=" * 60)

        item = {"name": name, "image": image, "price": price, "in_stock": stock}
        items.append(item)

    return items


def main_flow():
    chrome_options = Options()
    chrome_options.binary_location = r"C:\Users\lucas\OneDrive\Documents\Lucas_Grocery_Project\GroceryApp\backend\Lib\chrome-win64\chrome.exe"
    chrome_lib_path = r"C:\Users\lucas\OneDrive\Documents\Lucas_Grocery_Project\GroceryApp\backend\Lib\chromedriver-win64\chromedriver.exe"
    service = Service(chrome_lib_path)

    driver = webdriver.Chrome(service=service, options=chrome_options)
    base_url = "https://www.heb.com"
    driver.get(base_url)
    cookie = {
        "name": "SHOPPING_STORE_ID",
        "value": "796",
        "domain": "www.heb.com",
        "path": "/",
        "secure": True,
    }
    driver.add_cookie(cookie)
    driver.get(f"{base_url}/weekly-ad/deals")
    items = []
    while True:
        items.extend(scrape_page(driver))
        time.sleep(2)
        try:
            next_button = driver.find_element(
                By.CSS_SELECTOR, '[data-qe-id="paginationNext"]'
            )
            next_href = next_button.get_attribute("href")
            if not next_href:
                break

            next_url = urljoin(base_url, next_href)
            driver.get(next_url)
        except:  # noqa: E722
            break

    driver.quit()
    save_to_json(items, "heb")
