import time
import logging
import requests
from config import GHO_BASE_URL, PAGE_SIZE, REQUEST_DELAY

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_BACKOFF = 2


def fetch_indicator(indicator_code: str, since_year: int | None = None) -> list[dict]:
    """
    Extract all records for a given indicator from the WHO GHO OData API.
    Handles pagination, optional incremental filtering, and retries.
    """
    url = f"{GHO_BASE_URL}/{indicator_code}"

    filters = ["SpatialDimType eq 'COUNTRY'"]
    if since_year is not None:
        filters.append(f"TimeDim gt {since_year}")

    base_params = {
        "$filter": " and ".join(filters),
        "$top":    PAGE_SIZE,
    }

    all_records: list[dict] = []
    skip = 0

    while True:
        params = {**base_params, "$skip": skip}
        logger.info(f"[{indicator_code}] Fetching page (skip={skip})")

        batch = _fetch_with_retry(url, params, indicator_code)

        if not batch:
            break

        all_records.extend(batch)
        logger.info(f"[{indicator_code}] +{len(batch)} records (total: {len(all_records)})")

        if len(batch) < PAGE_SIZE:
            break

        skip += PAGE_SIZE
        time.sleep(REQUEST_DELAY)

    logger.info(f"[{indicator_code}] Extraction complete: {len(all_records)} records")
    return all_records


def _fetch_with_retry(url: str, params: dict, indicator_code: str) -> list[dict]:
    """
    GET the URL with retries on network/5xx errors.
    4xx errors are not retried — they indicate a logic error, not a transient failure.
    """
    delay = RETRY_BACKOFF
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json().get("value", [])

        except requests.exceptions.Timeout:
            logger.warning(f"[{indicator_code}] Timeout on attempt {attempt}/{MAX_RETRIES}")

        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response else "?"
            if e.response is not None and 400 <= e.response.status_code < 500:
                logger.error(f"[{indicator_code}] Client error {status} — not retrying")
                raise
            logger.warning(f"[{indicator_code}] Server error {status} on attempt {attempt}/{MAX_RETRIES}")

        except requests.exceptions.RequestException as e:
            logger.warning(f"[{indicator_code}] Request error on attempt {attempt}/{MAX_RETRIES}: {e}")

        if attempt < MAX_RETRIES:
            logger.info(f"[{indicator_code}] Retrying in {delay}s...")
            time.sleep(delay)
            delay *= 2

    raise RuntimeError(f"[{indicator_code}] All {MAX_RETRIES} fetch attempts failed.")