"""FastAPI service that compares refrigerator items against weekly ads using GPT."""

from __future__ import annotations

import base64
import json
import time
import os
from pathlib import Path
from typing import Sequence

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
WEEKLY_AD_BASE_PATH = Path("crawler/grocery_data")
DEFAULT_STORE_SLUGS = ("kroger", "heb", "tomthumb")
STORE_DISPLAY_NAMES = {
    "tomthumb": "TomThumb",
    "kroger": "Kroger",
    "heb": "HEB",
}
WEEKLY_AD_FILENAME = "weekly_ad.json"

app = FastAPI(title="Fridge Analyzer API")


def extract_store_metadata(weekly_ad_path: str | Path) -> tuple[str, str]:
    weekly_path = Path(weekly_ad_path)
    try:
        store_week = weekly_path.parent.name
        store_slug = weekly_path.parent.parent.name
    except IndexError:
        return "unknown", "unknown"
    store_name = STORE_DISPLAY_NAMES.get(store_slug.lower(), store_slug.title())
    return store_name, store_week


def _load_image_base64(weekly_ad_dir: Path, image_filename: str | None) -> str | None:
    if not image_filename:
        return None
    image_path = weekly_ad_dir / image_filename
    if not image_path.exists():
        return None
    return base64.b64encode(image_path.read_bytes()).decode("utf-8")


def _normalize_overlapping_ads(
    overlapping_ads, weekly_ad_path: Path, store_name: str, store_week: str
):
    if not isinstance(overlapping_ads, list):
        return overlapping_ads

    weekly_dir = weekly_ad_path.parent
    normalized = []
    for entry in overlapping_ads:
        if not isinstance(entry, dict):
            continue
        enriched = dict(entry)
        enriched.setdefault("store_name", store_name)
        enriched.setdefault("store_week", store_week)

        image_filename = None
        for key in ("image", "image_filename", "ad_image", "image_file"):
            candidate = enriched.get(key)
            if isinstance(candidate, str) and candidate.strip():
                image_filename = candidate.strip()
                break
        if image_filename:
            enriched["image_filename"] = image_filename
        image_b64 = _load_image_base64(weekly_dir, image_filename)
        if image_b64:
            enriched["image_base64"] = image_b64

        normalized.append(enriched)

    return normalized


def _discover_weekly_ad_paths(
    stores: Sequence[str], *, target_week: str | None = None, base_path: Path = WEEKLY_AD_BASE_PATH
) -> list[Path]:
    base_path = Path(base_path)
    weekly_paths: list[Path] = []
    for store in stores:
        store_slug = store.lower()
        store_dir = base_path / store_slug
        if not store_dir.exists():
            raise FileNotFoundError(f"Store directory not found for '{store}': {store_dir}")

        if target_week:
            week_candidates = [target_week]
        else:
            week_candidates = sorted(
                (p.name for p in store_dir.iterdir() if p.is_dir()),
                reverse=True,
            )
        if not week_candidates:
            raise FileNotFoundError(f"No weekly ad folders found for '{store}'.")

        selected_path: Path | None = None
        for week_name in week_candidates:
            candidate = store_dir / week_name / WEEKLY_AD_FILENAME
            if candidate.exists():
                selected_path = candidate
                break
        if not selected_path:
            raise FileNotFoundError(
                f"No {WEEKLY_AD_FILENAME} file found for '{store}' (searched weeks: {week_candidates})."
            )

        weekly_paths.append(selected_path)

    return weekly_paths


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
    weekly_payloads: Sequence[dict[str, str]],
    fridge_items_json: str,
    *,
    summary_style: str = "Return JSON array where each entry contains the overlapping refrigerator `item_name`, whether it is perishable, and the matching weekly ad fields such as `product`, `price`, `image_filename`, `store_name`, and `store_week`.",
):
    if not weekly_payloads:
        raise ValueError("At least one weekly ad payload is required.")

    instructions = (
        "You receive one refrigerator inspection JSON document and multiple weekly ad JSON documents. "
        "Find products that describe the same item (case-insensitive, allow close matches). "
        f"{summary_style} Copy `store_name`, `store_week`, and `image_filename` exactly from the matching weekly ad entry. "
        "If nothing overlaps, respond with an empty JSON array. Use only the store metadata provided below; do not invent new store names or weeks."
    )

    content = [
        {"type": "text", "text": instructions},
        {"type": "text", "text": f"Refrigerator JSON:\n{fridge_items_json}"},
    ]

    for payload in weekly_payloads:
        store_name = payload.get("store_name", "unknown")
        store_week = payload.get("store_week", "unknown")
        store_slug = payload.get("store_slug")
        weekly_json = payload.get("weekly_ad_json", "{}")
        slug_suffix = f" (store_slug={store_slug})" if store_slug else ""
        content.append(
            {
                "type": "text",
                "text": (
                    f"Weekly ad JSON for store_name='{store_name}'{slug_suffix} and store_week='{store_week}':\n"
                    f"{weekly_json}"
                ),
            }
        )

    response = client.chat.completions.create(
        model="gpt-5",
        messages=[{"role": "user", "content": content}],
    )

    return response.choices[0].message.content


def analyze_refrigerator(
    image_bytes: bytes,
    prompt: str = DEFAULT_PROMPT,
    weekly_ad_path: Path | str | None = None,
    *,
    stores: Sequence[str] | None = None,
    target_week: str | None = None,
):
    if weekly_ad_path and stores:
        raise ValueError("Provide either `weekly_ad_path` or `stores`, not both.")

    image_b64 = encode_image_bytes(image_bytes)
    fridge_raw, payload_len, duration = call_gpt(prompt, image_b64)

    try:
        fridge_items = json.loads(fridge_raw)
    except json.JSONDecodeError as exc:
        raise ValueError("GPT fridge response was not valid JSON.") from exc

    if weekly_ad_path:
        weekly_paths = [Path(weekly_ad_path)]
    else:
        store_slugs = tuple(store.lower() for store in (stores or DEFAULT_STORE_SLUGS))
        weekly_paths = _discover_weekly_ad_paths(store_slugs, target_week=target_week)

    store_infos: list[dict[str, str]] = []
    weekly_payloads: list[dict[str, str]] = []

    for path in weekly_paths:
        store_name, store_week = extract_store_metadata(path)
        try:
            store_slug = path.parent.parent.name
        except Exception:  # pragma: no cover - defensive path parsing
            store_slug = "unknown"

        store_info = {
            "store_name": store_name,
            "store_week": store_week,
            "weekly_ad_path": str(path),
        }
        store_infos.append(store_info)

        weekly_payloads.append(
            {
                "store_name": store_name,
                "store_week": store_week,
                "store_slug": store_slug,
                "weekly_ad_json": path.read_text(),
            }
        )

    overlap_raw = find_overlapping_weekly_ads(weekly_payloads, fridge_raw)
    aggregated_ads: list[object] = []
    store_overlaps: list[dict[str, object]] = []

    try:
        overlapping_ads = json.loads(overlap_raw)
    except json.JSONDecodeError:
        overlapping_ads = overlap_raw  # return raw text if parsing fails

    if isinstance(overlapping_ads, list):
        grouped_ads: dict[tuple[str, str], list[dict[str, object]]] = {}
        unknown_entries: list[object] = []
        for entry in overlapping_ads:
            if not isinstance(entry, dict):
                unknown_entries.append(entry)
                continue
            key = (entry.get("store_name"), entry.get("store_week"))
            if None in key:
                unknown_entries.append(entry)
                continue
            grouped_ads.setdefault(key, []).append(entry)

        known_keys = {(info["store_name"], info["store_week"]) for info in store_infos}
        for info in store_infos:
            key = (info["store_name"], info["store_week"])
            normalized_ads = _normalize_overlapping_ads(
                grouped_ads.get(key, []),
                Path(info["weekly_ad_path"]),
                info["store_name"],
                info["store_week"],
            )
            store_overlaps.append({**info, "ads": normalized_ads})
            if isinstance(normalized_ads, list):
                aggregated_ads.extend(normalized_ads)
            else:
                aggregated_ads.append({**info, "raw_response": normalized_ads})

        for key, entries in grouped_ads.items():
            if key not in known_keys:
                aggregated_ads.extend(entries)

        aggregated_ads.extend(unknown_entries)
    else:
        for info in store_infos:
            store_overlaps.append({**info, "ads": overlapping_ads})
            aggregated_ads.append({**info, "raw_response": overlapping_ads})

    store_info_payload: object
    if len(store_infos) == 1:
        store_info_payload = store_infos[0]
    else:
        store_info_payload = store_infos

    return {
        "fridge_items": fridge_items,
        "overlapping_ads": aggregated_ads,
        "store_info": store_info_payload,
        "store_overlaps": store_overlaps,
        "metrics": {
            "payload_chars": payload_len,
            "duration_seconds": duration,
            "stores_processed": len(weekly_paths),
        },
    }

