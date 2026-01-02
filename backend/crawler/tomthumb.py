import time
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def extract_tomthumb_deal(card):
    try:
        item_name = ""
        price_text = ""

        # Use image alt as a backup for name
        try:
            img = card.find_element(By.TAG_NAME, "img")
            img_url = img.get_attribute("src")
            item_name = img.get_attribute("alt").strip()
        except Exception:
            img_url = "N/A"

        # Try splitting the aria-label text
        try:
            button = card.find_element(By.CSS_SELECTOR, "button[data-product-id]")
            label = button.get_attribute("aria-label").strip()
            # Expected format: "Product Name, , $1.99 . Select for details."
            parts = label.split("$")
            if len(parts) >= 2:
                item_name = parts[0].split(",")[0].strip()
                price_text = "$" + parts[1].split(" ")[0].strip()
        except Exception:
            pass

        return item_name, img_url, price_text

    except Exception as e:
        print(f"[!] Failed to extract deal: {e}")
        return None, None, None


def main_flow():
    chrome_options = Options()
    chrome_options.binary_location = r"C:\Users\lucas\OneDrive\Documents\Lucas_Grocery_Project\GroceryApp\backend\Lib\chrome-win64\chrome.exe"
    chrome_lib_path = r"C:\Users\lucas\OneDrive\Documents\Lucas_Grocery_Project\GroceryApp\backend\Lib\chromedriver-win64\chromedriver.exe"
    service = Service(chrome_lib_path)

    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.get("https://tomthumb.com/weekly-ad")

    try:
        WebDriverWait(driver, 20).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "[data-product-id]"))
        )
    except Exception as e:
        print(f"[!] Timeout waiting for product cards: {e}")
        driver.quit()
        return

    time.sleep(2)  # random delay could go here

    try:
        cards = driver.find_elements(By.CSS_SELECTOR, "[data-product-id]")
    except Exception as e:
        print(f"[!] Error finding product cards: {e}")
        driver.quit()
        return

    for card in cards:
        name, image, price = extract_tomthumb_deal(card)
        if name:
            print("Product:", name)
            print("Image URL:", image)
            print("Price:", price)
            print("=" * 60)

    driver.quit()


if __name__ == "__main__":
    main_flow()
