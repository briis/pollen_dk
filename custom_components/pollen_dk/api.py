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
        (0, "none"),
        (5, "low"),
        (50, "moderate"),
        (500, "high"),
        (float("inf"), "very_high"),
    ],
    "graes": [
        (0, "none"),
        (5, "low"),
        (50, "moderate"),
        (500, "high"),
        (float("inf"), "very_high"),
    ],
    "el": [
        (0, "none"),
        (5, "low"),
        (50, "moderate"),
        (200, "high"),
        (float("inf"), "very_high"),
    ],
    "hassel": [
        (0, "none"),
        (5, "low"),
        (50, "moderate"),
        (200, "high"),
        (float("inf"), "very_high"),
    ],
    "bynke": [
        (0, "none"),
        (5, "low"),
        (10, "moderate"),
        (30, "high"),
        (float("inf"), "very_high"),
    ],
    "elm": [
        (0, "none"),
        (5, "low"),
        (50, "moderate"),
        (200, "high"),
        (float("inf"), "very_high"),
    ],
    # Mold spores use different scale
    "alternaria": [
        (0, "none"),
        (100, "low"),
        (1000, "moderate"),
        (5000, "high"),
        (float("inf"), "very_high"),
    ],
    "cladosporium": [
        (0, "none"),
        (3000, "low"),
        (10000, "moderate"),
        (50000, "high"),
        (float("inf"), "very_high"),
    ],
}


def get_severity(pollen_type: str, count: int | None) -> str:
    """Return severity label for a given pollen count."""
    if count is None or count < 0:
        return "unknown"
    thresholds = SEVERITY_LEVELS.get(pollen_type, SEVERITY_LEVELS["birk"])
    for threshold, label in thresholds:
        if count <= threshold:
            return label
    return "very_high"


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
              "birk": {"count": 42, "severity": "moderate", "forecast": "..."},
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

    @staticmethod
    def _parse_predictions(allergen: dict[str, Any]) -> dict[str, int | None]:
        # `overrides` (one entry per sorted prediction date) is a fallback
        # count used when the ML `prediction` field is empty.
        overrides: list[Any] = allergen.get("overrides") or []
        result: dict[str, int | None] = {}
        for i, date_key in enumerate(sorted(allergen.get("predictions") or {})):
            pred_data = allergen["predictions"][date_key]
            if isinstance(pred_data, dict):
                pred_str = pred_data.get("prediction", "")
            else:
                pred_str = ""
            if not pred_str and i < len(overrides):
                pred_str = str(overrides[i]) if overrides[i] is not None else ""
            try:
                result[date_key] = int(pred_str) if pred_str else None
            except ValueError, TypeError:
                result[date_key] = None
        return result

    @staticmethod
    def _compute_region_forecast(
        region_data: dict[str, Any],
    ) -> dict[str, str]:
        """Return worst severity per forecast date across all allergens."""
        sev_order = ["none", "low", "moderate", "high", "very_high"]
        region_forecast: dict[str, str] = {}
        for pk in POLLEN_TYPES:
            allergen_forecast = region_data.get(pk, {}).get("forecast", {})
            for date_key, pred_count in allergen_forecast.items():
                if pred_count is None:
                    continue
                sev = get_severity(pk, pred_count)
                if sev not in sev_order:
                    continue
                current = region_forecast.get(date_key, "none")
                if sev_order.index(sev) > sev_order.index(current):
                    region_forecast[date_key] = sev
        return region_forecast

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

            region_data: dict[str, Any] = {"last_update": station.get("date", "")}

            for allergen_id, allergen in (station.get("data") or {}).items():
                pollen_key = _ALLERGEN_ID_TO_KEY.get(str(allergen_id))
                if pollen_key is None or not isinstance(allergen, dict):
                    continue

                raw_level = allergen.get("level")
                in_season = allergen.get("inSeason", False)
                if raw_level is None or int(raw_level) < 0 or not in_season:
                    count = None
                else:
                    count = int(raw_level)

                region_data[pollen_key] = {
                    "count": count,
                    "severity": get_severity(pollen_key, count),
                    "name_da": pollen_key,
                    "name_en": POLLEN_TYPES[pollen_key],
                    "forecast": self._parse_predictions(allergen),
                }

            for pollen_key, pollen_name_en in POLLEN_TYPES.items():
                if pollen_key not in region_data:
                    region_data[pollen_key] = {
                        "count": None,
                        "severity": get_severity(pollen_key, None),
                        "name_da": pollen_key,
                        "name_en": pollen_name_en,
                        "forecast": {},
                    }

            region_data["forecast"] = self._compute_region_forecast(region_data)
            result[region_key] = region_data

        return result
