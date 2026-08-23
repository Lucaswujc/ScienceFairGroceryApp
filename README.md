# Smart Cart Grocery App

Smart Cart helps users reduce grocery costs and food waste by combining:
- Weekly ad browsing across multiple stores.
- A shared shopping cart for selected deal items.
- Refrigerator photo analysis to identify perishables and suggest overlapping deals.

## Project Goals

1. Let users browse weekly promotions by store and week.
2. Make it easy to build a consolidated shopping cart.
3. Use fridge-image analysis to prioritize food usage and auto-surface matching ads.

## Weekly Project Checks 

### Week of 2026-02-23
Achievements:
 - Presented project at 2026 Dallas Regional Science and Engineering Fair (DRSEF)
### Week of 2026 02-09
Achievements:
 - Ran dry run with neighbors and friends for feedback
### Week of 2026-02-02
Achievements:
- Packaged application in docker, deployed to home network and exposed to internet for testing
### Week of 2026-01-19

Achievements:
- Added/expanded cart and analyzer features (`cart and analyzer features`).
- Fixed ad matching behavior (`ad matcher fix`).

TODO for next weekly check:
- Add tests for cart totals, deduplication, and analyzer overlap normalization.
- Validate analyzer UX and error handling for slow/failed API responses.
- Confirm ad matcher quality with a broader sample of products and synonyms.

### Week of 2026-01-12

Achievements:
- Improved crawler and config reliability (`heb crawler fix`, `crawler config module fix`).
- Added Docker data-volume support for backend ad data.
- Added env-based frontend API base URL.
- Fixed image-analysis flow and updated home page copy/experience.
- Cleaned up repository ignore rules and merged multiple development PRs.

TODO for next weekly check:
- Add integration tests for file-based ad serving and image byte endpoint.
- Standardize week/date format validation across crawler, API, and frontend.
- Document expected crawler output schema and enforce it with lightweight validation.

### Week of 2026-01-05

Achievements:
- Added Docker build/compose support and updated backend requirements.
- Merged development work into mainline.

TODO for next weekly check:
- Add a one-command local startup script or task (`docker compose up` + env checks).
- Add CI checks for lint/test/build of backend and frontend.
- Add health/readiness checks for backend container.

### Week of 2025-12-29

Achievements:
- Fixed path/CORS issues in backend.
- Switched image loading to API-per-image approach.
- Cleaned up tabs and improved Monday-selection UI.
- Performed early frontend navigation/home updates and merged development PRs.

TODO for next weekly check:
- Add endpoint-level API tests for CORS, missing params, and 404 behavior.
- Cache/reuse image responses where appropriate to reduce repeated network calls.
- Improve frontend loading/empty/error states for ad retrieval.

## Suggested Next Enhancements

1. Add a test matrix covering API, analyzer normalization, and frontend basket logic.
2. Add observability (structured logs + request timing) for crawler and analysis APIs.
3. Add a scheduled crawler run with status reporting per store/week.

## General Architecture

The project is split into a React Native frontend, a FastAPI backend, and crawler/storage layers.

```text
Frontend (Expo React Native)
	-> calls HTTP APIs

Backend (FastAPI)
	-> serves weekly ads from JSON file storage
	-> serves image bytes
	-> runs fridge analysis + overlap matching

Data Sources
	-> crawler outputs weekly_ad.json + product images per store/week
	-> optional SQLite table for crawler_results

Infrastructure
	-> docker-compose runs frontend + backend
	-> shared volumes persist DB and weekly ad data
```

## Main Components And Functions

### Frontend (mobile/web UI)

- `frontend/app/(tabs)/ads.tsx`
	- `fetchAdsForSelection(...)`: fetches weekly ads for selected store(s) and week.
	- `getMondayISO(...)`, `getAdjacentMondays(...)`: date helpers for Monday-based ad selection.
- `frontend/app/utility.tsx`
	- `get_store_ads(...)`: calls `/weeklyadfromfile/`.
	- `get_image(...)`: calls `/getimagebytes/` and converts to a displayable data URI.
	- `analyze_photo(...)`: uploads a fridge image to `/analyze-fridge/` (with fallback endpoint attempts).
- `frontend/app/(tabs)/analyzer.tsx`
	- `handlePickImage()`, `handleAnalyze()`: user flow for selecting and analyzing fridge photos.
	- `normalizeOverlapEntries(...)`: normalizes backend overlap payloads for display and add-to-cart actions.
- `frontend/context/BasketContext.tsx`
	- `addToBasket(...)`, `removeFromBasket(...)`, `clearBasket(...)`, `isInBasket(...)`: shared cart state and de-duplication.
- `frontend/app/(tabs)/cart.tsx`
	- `priceToNumber(...)`: parses price strings for subtotal/total estimation.
	- Grouped cart rendering by store with note-taking support.

### Backend (API + analysis)

- `backend/app.py`
	- Uvicorn entry point that serves the FastAPI app.
- `backend/api.py`
	- `GET /weeklyad/`: returns weekly ads from SQLite (with image base64 payload).
	- `GET /weeklyadfromfile/`: returns weekly ads from crawler JSON output.
	- `GET /getimagebytes/`: returns base64-encoded image content by filename.
	- `POST /analyze-fridge/`: analyzes fridge photo and returns matched weekly ads.
- `backend/fridge_analyzer.py`
	- `analyze_refrigerator(...)`: end-to-end orchestration for vision extraction + ad overlap matching.
	- `_discover_weekly_ad_paths(...)`: resolves latest/target week ad files per store.
	- `find_overlapping_weekly_ads(...)`: asks GPT to match fridge items against store weekly ads.
	- `_normalize_overlapping_ads(...)`: enriches overlap entries with store metadata and base64 images.

### Crawler And Storage Utilities

- `backend/crawler/utility.py`
	- `download_image(...)`: downloads and stores ad images per store/week.
	- `save_grocery_items(...)`: appends/store weekly ad JSON data.
	- `get_store_ads(...)`: reads weekly ad JSON for API consumption.
	- `get_store_week_folder(...)`, `get_json_file_path(...)`: canonical storage paths.
- `backend/db_engine/sqlite_engine.py`
	- `init_db()`, `get_connection()`: DB bootstrap and connection.
	- `insert_crawler_result(...)`: persists crawler rows to SQLite.

## Runtime And Deployment

- `docker-compose.yaml` runs two services:
	- `backend` on port `8000`.
	- `frontend` on port `8081` (plus Expo ports).
- Data persistence:
	- `./db_store -> /app/db_store`
	- `./store_data -> /app/crawler/grocery_data`
- Required environment variables:
	- `OPENAI_API_KEY`
	- `EXPO_PUBLIC_API_BASE`

