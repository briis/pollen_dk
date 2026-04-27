"""API client for Astma-Allergi Danmark pollen data."""

from __future__ import annotations

import json
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

# Firestore station ID → region key (from the select#box1 on astma-allergi.dk)
_STATION_ID_TO_REGION: dict[str, str] = {
    "48": "koebenhavn",
    "49": "viborg",
}

# Firestore pollen type ID → our internal key (from POLLEN_NAMES in pollen.js)
_ALLERGEN_ID_TO_KEY: dict[str, str] = {
    "7": "birk",
    "31": "bynke",
    "1": "el",
    "4": "elm",
    "28": "graes",
    "2": "hassel",
    "44": "alternaria",
    "45": "cladosporium",
}

# Severity thresholds (grains/m³) - based on Astma-Allergi Danmark guidelines
SEVERITY_LEVELS = {
    "birk": [
        (0, "ingen"),
        (5, "lav"),
        (50, "moderat"),
        (500, "høj"),
        (float("inf"), "meget høj"),
    ],
    "graes": [
        (0, "ingen"),
        (5, "lav"),
        (50, "moderat"),
        (500, "høj"),
        (float("inf"), "meget høj"),
    ],
    "el": [
        (0, "ingen"),
        (5, "lav"),
        (50, "moderat"),
        (200, "høj"),
        (float("inf"), "meget høj"),
    ],
    "hassel": [
        (0, "ingen"),
        (5, "lav"),
        (50, "moderat"),
        (200, "høj"),
        (float("inf"), "meget høj"),
    ],
    "bynke": [
        (0, "ingen"),
        (5, "lav"),
        (10, "moderat"),
        (30, "høj"),
        (float("inf"), "meget høj"),
    ],
    "elm": [
        (0, "ingen"),
        (5, "lav"),
        (50, "moderat"),
        (200, "høj"),
        (float("inf"), "meget høj"),
    ],
    # Mold spores use different scale
    "alternaria": [
        (0, "ingen"),
        (100, "lav"),
        (1000, "moderat"),
        (5000, "høj"),
        (float("inf"), "meget høj"),
    ],
    "cladosporium": [
        (0, "ingen"),
        (3000, "lav"),
        (10000, "moderat"),
        (50000, "høj"),
        (float("inf"), "meget høj"),
    ],
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
        """Initialise the API client with an aiohttp session."""
        self._session = session

    async def async_get_pollen_data(self) -> dict[str, Any]:
        """
        Fetch and parse pollen data from the API.

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
                raw = await response.json(content_type=None)
                # The endpoint wraps the Firestore document in an extra JSON string
                data = json.loads(raw) if isinstance(raw, str) else raw
        except aiohttp.ClientResponseError as err:
            msg = f"HTTP error fetching pollen data: {err.status} {err.message}"
            raise PollenDKApiError(msg) from err
        except aiohttp.ClientError as err:
            msg = f"Network error fetching pollen data: {err}"
            raise PollenDKApiError(msg) from err
        except Exception as err:
            msg = f"Unexpected error fetching pollen data: {err}"
            raise PollenDKApiError(msg) from err

        return self._parse_response(data)

    @staticmethod
    def _firestore_value(node: Any) -> Any:
        """Recursively unwrap a Firestore REST value node into a plain Python value."""
        if not isinstance(node, dict):
            return node
        if "mapValue" in node:
            fields = node["mapValue"].get("fields") or {}
            return {k: PollenDKApi._firestore_value(v) for k, v in fields.items()}
        if "arrayValue" in node:
            values = node["arrayValue"].get("values") or []
            return [PollenDKApi._firestore_value(v) for v in values]
        for key, cast in (("integerValue", int), ("doubleValue", float)):
            if key in node:
                return cast(node[key])
        for key in ("stringValue", "booleanValue", "nullValue"):
            if key in node:
                return node[key]
        return {k: PollenDKApi._firestore_value(v) for k, v in node.items()}

    def _parse_response(self, data: Any) -> dict[str, Any]:
        """
        Parse the Firestore REST response into a structured dict.

        The API returns a single Firestore document.  Top-level numeric keys
        (48 = København, 49 = Viborg) are station IDs.  Inside each station the
        "data" map uses numeric allergen IDs (7 = birk, 28 = græs, …).
        """
        result: dict[str, Any] = {}

        if not isinstance(data, dict):
            _LOGGER.warning("Unexpected pollen API response type: %s", type(data))
            return result

        raw_fields = data.get("fields", {})
        if not raw_fields:
            _LOGGER.warning("Pollen API response has no 'fields' key")
            return result

        for station_id, station_node in raw_fields.items():
            region_key = _STATION_ID_TO_REGION.get(station_id)
            if region_key is None:
                _LOGGER.debug(
                    "Unknown station ID in pollen API response: %s", station_id
                )
                continue

            station = self._firestore_value(station_node)
            if not isinstance(station, dict):
                continue

            date_str = station.get("date", "")
            allergens_raw = station.get("data") or {}

            region_data: dict[str, Any] = {
                "last_update": date_str,
                "forecast_text": "",
            }

            for allergen_id, allergen in allergens_raw.items():
                pollen_key = _ALLERGEN_ID_TO_KEY.get(str(allergen_id))
                if pollen_key is None:
                    continue
                if not isinstance(allergen, dict):
                    continue

                raw_level = allergen.get("level")
                in_season = allergen.get("inSeason", False)

                # -1 means no measurement; also treat out-of-season as no data
                if raw_level is None or int(raw_level) < 0 or not in_season:
                    count = None
                else:
                    count = int(raw_level)

                region_data[pollen_key] = {
                    "count": count,
                    "severity": get_severity(pollen_key, count),
                    "name_da": pollen_key,
                    "name_en": POLLEN_TYPES[pollen_key],
                }

            # Fill any missing pollen types so sensors always have an entry
            for pollen_key, pollen_name_en in POLLEN_TYPES.items():
                if pollen_key not in region_data:
                    region_data[pollen_key] = {
                        "count": None,
                        "severity": get_severity(pollen_key, None),
                        "name_da": pollen_key,
                        "name_en": pollen_name_en,
                    }

            result[region_key] = region_data

        return result
