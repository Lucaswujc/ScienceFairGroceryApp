import os
import re
import urllib.request


def download_image(url, name):
    # Locate 'grocery_images' folder relative to this script
    base_dir = os.path.dirname(os.path.abspath(__file__))
    folder_path = os.path.join(base_dir, "grocery_images")

    # Check if the folder exists
    if not os.path.isdir(folder_path):
        print(f"Folder 'grocery_images' not found at {folder_path}. Skipping download.")
        return None

    # Sanitize filename
    filename = re.sub(r"[^\w\-_\. ]", "_", name)[:50]
    ext = os.path.splitext(url)[-1].split("?")[0]
    if not ext or len(ext) > 5:
        ext = ".jpg"  # Fallback extension if unknown

    local_path = os.path.join(folder_path, f"{filename}{ext}")

    # Download image using urlopen
    try:
        with (
            urllib.request.urlopen(url) as response,
            open(local_path, "wb") as out_file,
        ):
            out_file.write(response.read())
        return local_path
    except Exception as e:
        print(f"Failed to download image for {name}: {e}")
        return None


def main_flow():
    # Example usage of download_image
    url = "https://s3.us-west-1.wasabisys.com/kroger/Kroger/Montages/M_343341.png"
    name = "Sample Product"
    local_path = download_image(url, name)
    if local_path:
        print(f"Image downloaded to: {local_path}")
    else:
        print("Image download failed.")


if __name__ == "__main__":
    main_flow()
    exit()
