"""API client for Astma-Allergi Danmark pollen data."""

from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)
_DD_MM_YYYY = re.compile(r"^(\d\d)-(\d\d)-(\d{4})$")
_OVERRIDE_SEVERITY_MAP: dict[int, str] = {
    0: "none",
    1: "low",
    2: "moderate",
    3: "high",
    4: "very_high",
}
_MAX_SEVERITY_INDEX = max(_OVERRIDE_SEVERITY_MAP)

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
    def _to_iso_date(date_key: str) -> str:
        """Convert DD-MM-YYYY to ISO YYYY-MM-DD."""
        m = _DD_MM_YYYY.match(date_key)
        return f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else date_key

    @staticmethod
    def _parse_predictions(allergen: dict[str, Any], pollen_key: str) -> dict[str, str]:
        # When the ML `prediction` field is non-empty it holds a grain count →
        # convert via get_severity.  When it is empty the `overrides` list
        # provides a 0-4 severity index that maps directly via _OVERRIDE_SEVERITY_MAP.
        overrides: list[Any] = allergen.get("overrides") or []
        result: dict[str, str] = {}
        raw_predictions = allergen.get("predictions") or {}
        sorted_raw_keys = sorted(raw_predictions, key=PollenDKApi._to_iso_date)
        for i, raw_key in enumerate(sorted_raw_keys):
            pred_data = raw_predictions[raw_key]
            iso_key = PollenDKApi._to_iso_date(raw_key)
            if isinstance(pred_data, dict):
                raw_val = pred_data.get("prediction")
            elif pred_data is not None:
                raw_val = pred_data
            else:
                raw_val = None
            pred_str = "" if raw_val is None or raw_val == "" else str(raw_val)
            if pred_str:
                try:
                    pred_num = round(float(pred_str))
                    if pred_num <= _MAX_SEVERITY_INDEX:
                        # Values 0-4 are severity indices (same scale as overrides)
                        result[iso_key] = _OVERRIDE_SEVERITY_MAP.get(pred_num, "none")
                    else:
                        result[iso_key] = get_severity(pollen_key, pred_num)
                    continue
                except ValueError, TypeError:
                    pass
            if i < len(overrides) and overrides[i] is not None:
                try:
                    result[iso_key] = _OVERRIDE_SEVERITY_MAP.get(
                        int(overrides[i]), "none"
                    )
                except ValueError, TypeError:
                    result[iso_key] = "none"
            else:
                result[iso_key] = "none"
        return result

    @staticmethod
    def _worst_severity(region_data: dict[str, Any]) -> str:
        """Return the highest severity across all in-season pollen types."""
        sev_order = ["none", "low", "moderate", "high", "very_high"]
        worst = "none"
        for pk in POLLEN_TYPES:
            sev = region_data.get(pk, {}).get("severity", "none")
            if sev in sev_order and sev_order.index(sev) > sev_order.index(worst):
                worst = sev
        return worst

    @staticmethod
    def _compute_region_forecast(
        region_data: dict[str, Any],
    ) -> dict[str, str]:
        """Return worst severity per forecast date across all allergens."""
        sev_order = ["none", "low", "moderate", "high", "very_high"]
        region_forecast: dict[str, str] = {}
        for pk in POLLEN_TYPES:
            allergen_forecast = region_data.get(pk, {}).get("forecast", {})
            for date_key, sev in allergen_forecast.items():
                if sev not in sev_order:
                    continue
                current = region_forecast.get(date_key, "")
                if not current or sev_order.index(sev) > sev_order.index(current):
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
                    "forecast": self._parse_predictions(allergen, pollen_key),
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

            today_iso = datetime.now(tz=UTC).date().isoformat()
            region_data["forecast"] = {
                k: v
                for k, v in self._compute_region_forecast(region_data).items()
                if k >= today_iso
            }
            region_data["forecast"][today_iso] = self._worst_severity(region_data)
            result[region_key] = region_data

        return result
