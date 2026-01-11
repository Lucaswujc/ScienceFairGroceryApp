"""FastAPI service that compares refrigerator items against weekly ads using GPT."""

from __future__ import annotations

import base64
import json
import time
import os
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from openai import OpenAI

API_KEY = os.environ.get("OPENAI_API_KEY")
if not API_KEY:
    raise RuntimeError("OPENAI_API_KEY environment variable is not set.")
client = OpenAI(api_key=API_KEY)

DEFAULT_PROMPT = (
    "Describe what's in this image. Identify each item and whether it is perishable, "
    "responding in JSON with item names as keys and booleans indicating perishability. "
    "Keep item names concise and avoid duplicates."
)
WEEKLY_AD_PATH = Path("crawler/grocery_data/tomthumb/2025-12-29/weekly_ad.json")

app = FastAPI(title="Fridge Analyzer API")


def encode_image_bytes(image_bytes: bytes) -> str:
    if not image_bytes:
        raise ValueError("Image payload is empty.")
    return base64.b64encode(image_bytes).decode("utf-8")

def call_gpt(prompt: str, image_b64: str):
    start = time.time()
    response = client.chat.completions.create(
        model="gpt-5",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
                ],
            }
        ],
    )
    elapsed = time.time() - start
    return response.choices[0].message.content, len(image_b64), elapsed

def chat_with_gpt(prompt: str) -> str:
    response = client.chat.completions.create(
        model="gpt-5",
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content


def find_overlapping_weekly_ads(
    weekly_ad_path: str | Path,
    fridge_items_json: str,
    *,
    summary_style: str = "Return JSON array where each entry contains the overlapping refrigerator `item_name`, whether it is perishable, and the matching weekly ad fields such as `product`, `price`, and `image`.",
):
    weekly_path = Path(weekly_ad_path)
    if not weekly_path.exists():
        raise FileNotFoundError(f"Weekly ad file not found: {weekly_path}")

    weekly_payload = weekly_path.read_text()
    instructions = (
        "You receive two JSON documents: one from a refrigerator inspection and one listing weekly ad products. "
        "Find items that describe the same product (case-insensitive, allow close matches). "
        f"{summary_style} If nothing overlaps, respond with an empty JSON array."
    )

    response = client.chat.completions.create(
        model="gpt-5",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": instructions},
                    {
                        "type": "text",
                        "text": f"Refrigerator JSON:\n{fridge_items_json}",
                    },
                    {
                        "type": "text",
                        "text": f"Weekly ad JSON:\n{weekly_payload}",
                    },
                ],
            }
        ],
    )

    return response.choices[0].message.content


def analyze_refrigerator(image_bytes: bytes, prompt: str = DEFAULT_PROMPT, weekly_ad_path: Path = WEEKLY_AD_PATH):
    image_b64 = encode_image_bytes(image_bytes)
    fridge_raw, payload_len, duration = call_gpt(prompt, image_b64)

    try:
        fridge_items = json.loads(fridge_raw)
    except json.JSONDecodeError as exc:
        raise ValueError("GPT fridge response was not valid JSON.") from exc

    overlap_raw = find_overlapping_weekly_ads(weekly_ad_path, fridge_raw)
    try:
        overlapping_ads = json.loads(overlap_raw)
    except json.JSONDecodeError:
        overlapping_ads = overlap_raw  # return raw text if parsing fails

    return {
        "fridge_items": fridge_items,
        "overlapping_ads": overlapping_ads,
        "metrics": {"payload_chars": payload_len, "duration_seconds": duration},
    }

