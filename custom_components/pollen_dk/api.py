"""API client for Astma-Allergi Danmark pollen data."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)

POLLEN_FEED_URL = "https://www.astma-allergi.dk/umbraco/Api/PollenApi/GetPollenFeed"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "da-DK,da;q=0.9,en;q=0.8",
    "Referer": "https://www.astma-allergi.dk/",
}

# Known pollen types reported by Astma-Allergi Danmark
POLLEN_TYPES = {
    "birk": "Birch",
    "bynke": "Mugwort",
    "el": "Alder",
    "elm": "Elm",
    "graes": "Grass",
    "hassel": "Hazel",
    "alternaria": "Alternaria",
    "cladosporium": "Cladosporium",
}

# Regions (measurement stations)
REGIONS = {
    "koebenhavn": "København (Østdanmark)",
    "viborg": "Viborg (Vestdanmark)",
}

# Severity thresholds (grains/m³) - based on Astma-Allergi Danmark guidelines
SEVERITY_LEVELS = {
    "birk": [(0, "ingen"), (5, "lav"), (50, "moderat"), (500, "høj"), (float("inf"), "meget høj")],
    "graes": [(0, "ingen"), (5, "lav"), (50, "moderat"), (500, "høj"), (float("inf"), "meget høj")],
    "el": [(0, "ingen"), (5, "lav"), (50, "moderat"), (200, "høj"), (float("inf"), "meget høj")],
    "hassel": [(0, "ingen"), (5, "lav"), (50, "moderat"), (200, "høj"), (float("inf"), "meget høj")],
    "bynke": [(0, "ingen"), (5, "lav"), (10, "moderat"), (30, "høj"), (float("inf"), "meget høj")],
    "elm": [(0, "ingen"), (5, "lav"), (50, "moderat"), (200, "høj"), (float("inf"), "meget høj")],
    # Mold spores use different scale
    "alternaria": [(0, "ingen"), (100, "lav"), (1000, "moderat"), (5000, "høj"), (float("inf"), "meget høj")],
    "cladosporium": [(0, "ingen"), (3000, "lav"), (10000, "moderat"), (50000, "høj"), (float("inf"), "meget høj")],
}


def get_severity(pollen_type: str, count: int | None) -> str:
    """Return severity label for a given pollen count."""
    if count is None or count < 0:
        return "ukendt"
    thresholds = SEVERITY_LEVELS.get(pollen_type, SEVERITY_LEVELS["birk"])
    for threshold, label in thresholds:
        if count <= threshold:
            return label
    return "meget høj"


class PollenDKApiError(Exception):
    """Exception for API errors."""


class PollenDKApi:
    """Client for Astma-Allergi Danmark pollen JSON feed."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        self._session = session

    async def async_get_pollen_data(self) -> dict[str, Any]:
        """Fetch and parse pollen data from the API.

        Returns a dict structured as:
        {
          "koebenhavn": {
              "birk": {"count": 42, "severity": "moderat", "forecast": "..."},
              "graes": {...},
              ...
              "last_update": "...",
              "forecast_text": "...",
          },
          "viborg": { ... }
        }
        """
        try:
            async with self._session.get(
                POLLEN_FEED_URL,
                headers=HEADERS,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                response.raise_for_status()
                data = await response.json(content_type=None)
        except aiohttp.ClientResponseError as err:
            raise PollenDKApiError(
                f"HTTP error fetching pollen data: {err.status} {err.message}"
            ) from err
        except aiohttp.ClientError as err:
            raise PollenDKApiError(f"Network error fetching pollen data: {err}") from err
        except Exception as err:
            raise PollenDKApiError(f"Unexpected error fetching pollen data: {err}") from err

        return self._parse_response(data)

    def _parse_response(self, data: Any) -> dict[str, Any]:
        """Parse the raw JSON API response into a structured dict."""
        result: dict[str, Any] = {}

        if not isinstance(data, (list, dict)):
            _LOGGER.warning("Unexpected pollen API response type: %s", type(data))
            return result

        # The API returns a list of region objects
        # Each item has a region identifier and pollen measurements
        items = data if isinstance(data, list) else data.get("items", [data])

        for item in items:
            if not isinstance(item, dict):
                continue

            region_raw = str(item.get("region", item.get("Region", ""))).lower()
            # Normalise: "københavn" -> "koebenhavn", "viborg" -> "viborg"
            if "benhavn" in region_raw or "st" in region_raw or "øst" in region_raw:
                region_key = "koebenhavn"
            elif "viborg" in region_raw or "vest" in region_raw:
                region_key = "viborg"
            else:
                _LOGGER.debug("Unknown region in API response: %s", region_raw)
                # Use the raw key if unknown
                region_key = region_raw or "unknown"

            region_data: dict[str, Any] = {
                "last_update": item.get("date", item.get("Date", item.get("lastUpdate", ""))),
                "forecast_text": item.get("forecast", item.get("Forecast", "")),
            }

            # Parse individual pollen counts
            # The API may use either lowercase or PascalCase keys
            for dk_key in POLLEN_TYPES:
                # Try multiple possible key formats
                count_value = (
                    item.get(dk_key)
                    or item.get(dk_key.capitalize())
                    or item.get(dk_key.title())
                    # "graes" might appear as "gras" or "grÃ¦s" in some responses
                    or (item.get("graes") if dk_key == "graes" else None)
                )

                if count_value is not None:
                    try:
                        count = int(count_value)
                    except (TypeError, ValueError):
                        count = None
                else:
                    count = None

                region_data[dk_key] = {
                    "count": count,
                    "severity": get_severity(dk_key, count),
                    "name_da": dk_key,
                    "name_en": POLLEN_TYPES[dk_key],
                }

            result[region_key] = region_data

        return result
