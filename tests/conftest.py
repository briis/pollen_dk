"""Shared fixtures and mock data for pollen_dk tests."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.pollen_dk.const import CONF_REGION, DOMAIN, REGION_KOEBENHAVN

# ── Firestore response helpers ────────────────────────────────────────────────


def _allergen_node(level: int, *, in_season: bool) -> dict:
    return {
        "mapValue": {
            "fields": {
                "level": {"integerValue": str(level)},
                "inSeason": {"booleanValue": in_season},
                "overrides": {"arrayValue": {}},
                "predictions": {"mapValue": {"fields": {}}},
            }
        }
    }


def _station_node(date: str, allergens: dict) -> dict:
    return {
        "mapValue": {
            "fields": {
                "date": {"stringValue": date},
                "data": {"mapValue": {"fields": allergens}},
            }
        }
    }


_KBH_ALLERGENS = {
    "7": _allergen_node(186, in_season=True),  # birk - in season
    "31": _allergen_node(-1, in_season=False),  # bynke
    "1": _allergen_node(-1, in_season=False),  # el
    "4": _allergen_node(-1, in_season=False),  # elm
    "28": _allergen_node(-1, in_season=False),  # graes
    "2": _allergen_node(-1, in_season=False),  # hassel
    "44": _allergen_node(-1, in_season=False),  # alternaria
    "45": _allergen_node(-1, in_season=False),  # cladosporium
}

_VIB_ALLERGENS = {
    "7": _allergen_node(60, in_season=True),  # birk - in season
    "31": _allergen_node(-1, in_season=False),
    "1": _allergen_node(-1, in_season=False),
    "4": _allergen_node(-1, in_season=False),
    "28": _allergen_node(-1, in_season=False),
    "2": _allergen_node(-1, in_season=False),
    "44": _allergen_node(-1, in_season=False),
    "45": _allergen_node(-1, in_season=False),
}

MOCK_FIRESTORE_RESPONSE: dict = {
    "fields": {
        "48": _station_node("26-04-2026", _KBH_ALLERGENS),
        "49": _station_node("26-04-2026", _VIB_ALLERGENS),
    },
}

# Pre-parsed form of MOCK_FIRESTORE_RESPONSE (København only)
MOCK_PARSED_DATA: dict = {
    "koebenhavn": {
        "last_update": "26-04-2026",
        "forecast_text": "",
        "birk": {
            "count": 186,
            "severity": "high",
            "name_da": "birk",
            "name_en": "Birch",
        },
        "bynke": {
            "count": None,
            "severity": "unknown",
            "name_da": "bynke",
            "name_en": "Mugwort",
        },
        "el": {
            "count": None,
            "severity": "unknown",
            "name_da": "el",
            "name_en": "Alder",
        },
        "elm": {
            "count": None,
            "severity": "unknown",
            "name_da": "elm",
            "name_en": "Elm",
        },
        "graes": {
            "count": None,
            "severity": "unknown",
            "name_da": "graes",
            "name_en": "Grass",
        },
        "hassel": {
            "count": None,
            "severity": "unknown",
            "name_da": "hassel",
            "name_en": "Hazel",
        },
        "alternaria": {
            "count": None,
            "severity": "unknown",
            "name_da": "alternaria",
            "name_en": "Alternaria",
        },
        "cladosporium": {
            "count": None,
            "severity": "unknown",
            "name_da": "cladosporium",
            "name_en": "Cladosporium",
        },
    },
}


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations for every test in this suite."""


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        data={CONF_REGION: REGION_KOEBENHAVN},
        unique_id=f"pollen_dk_{REGION_KOEBENHAVN}",
    )


@pytest.fixture
async def setup_integration(hass, mock_config_entry):
    """Set up the integration with mocked API data returning MOCK_PARSED_DATA."""
    mock_config_entry.add_to_hass(hass)
    with patch(
        "custom_components.pollen_dk.api.PollenDKApi.async_get_pollen_data",
        return_value=MOCK_PARSED_DATA,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
    return mock_config_entry
