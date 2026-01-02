from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from db_engine.sqlite_engine import get_connection
from crawler.utility import get_store_ads

app = FastAPI()

# CORS configuration - adjust `allow_origins` for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/weeklyad/")
def get_weekly_ad(storename: str = Query(...), week: str = Query(...)):
    """
    Retrieve weekly ad for a store for a particular week.
    week should be in YYYY-MM-DD format (weekly_ad_starting_date).
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT product, price, image FROM crawler_results WHERE storename = ? AND weekly_ad_starting_date = ?""",
            (storename, week),
        )
        rows = cursor.fetchall()
        if not rows:
            raise HTTPException(
                status_code=404, detail="No weekly ad found for this store and week."
            )
        # Return image as base64 string for API response
        import base64

        results = []
        for product, price, image in rows:
            img_b64 = base64.b64encode(image).decode() if image else None
            results.append(
                {"product": product, "price": price, "image_base64": img_b64}
            )
        return results

@app.get("/weeklyadfromfile/")
def get_weekly_ad_from_file(storename: str = Query(...), week: str = Query(...)):
    """
    Retrieve weekly ad for a store for a particular week from a JSON file.
    week should be in YYYY-Www format (ISO week date).
    """
    try:
        data = get_store_ads(storename, week)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="No weekly ad file found for this store and week.",
        )

    return data



@app.get("/getimagebytes/")
def get_image_bytes(
    storename: str = Query(...),
    week: str = Query(...),
    image_filename: str = Query(...),
):
    """
    Retrieve image bytes for a given image filename from the store's weekly ad folder.
    week should be in YYYY-MM-DD format (weekly_ad_starting_date).
    """
    import os
    import base64
    from crawler.utility import get_store_week_folder

    folder_path = get_store_week_folder(storename, week)
    file_path = os.path.join(folder_path, image_filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Image file not found.")

    with open(file_path, "rb") as f:
        image_bytes = f.read()

    image_b64 = base64.b64encode(image_bytes).decode()
    return {"image_bytes": image_b64}