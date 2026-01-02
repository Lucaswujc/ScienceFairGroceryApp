import logging
import requests


def fetch_image_bytes(image_url, timeout=10):
    """
    Download image from the given URL and return its bytes.
    Returns None if download fails.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        # "Sec-Fetch-Dest": "document",  # Not needed for requests, only browsers
        # "Sec-Fetch-Mode": "navigate",   # Not needed for requests, only browsers
        # "Sec-Fetch-Site": "none",       # Not needed for requests, only browsers
    }
    try:
        response = requests.get(image_url, timeout=timeout, headers=headers)
        response.raise_for_status()
        return response.content
    except (requests.Timeout, requests.ConnectionError) as e:
        logging.error(f"Image download failed (timeout/connection): {e}")
        return None
    except requests.HTTPError as e:
        logging.error(f"Image download failed (HTTP error): {e}")
        return None
    except Exception as e:
        logging.error(f"Image download failed (other error): {e}")
        return None
