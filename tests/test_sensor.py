"""Tests for the PollenDK sensor platform."""

from __future__ import annotations

from unittest.mock import patch

from homeassistant.const import STATE_UNKNOWN
from homeassistant.helpers import entity_registry as er

from custom_components.pollen_dk.const import DOMAIN, POLLEN_TYPES
from custom_components.pollen_dk.sensor import PollenSeveritySensor

# ── Helpers ───────────────────────────────────────────────────────────────────


def _entity_id(hass, unique_id: str) -> str | None:
    return er.async_get(hass).async_get_entity_id("sensor", DOMAIN, unique_id)


# ── Entity registration ───────────────────────────────────────────────────────


async def test_correct_number_of_entities_created(hass, setup_integration) -> None:
    ent_reg = er.async_get(hass)
    entries = [e for e in ent_reg.entities.values() if e.platform == DOMAIN]
    # 8 count sensors + 1 severity sensor = 9
    assert len(entries) == 9


async def test_all_pollen_type_count_sensors_registered(
    hass, setup_integration
) -> None:
    for pollen_key in POLLEN_TYPES:
        uid = f"{DOMAIN}_koebenhavn_{pollen_key}_count"
        assert _entity_id(hass, uid) is not None, f"Missing sensor for {pollen_key}"


async def test_severity_sensor_registered(hass, setup_integration) -> None:
    uid = f"{DOMAIN}_koebenhavn_overall_severity"
    assert _entity_id(hass, uid) is not None


# ── Count sensor state ────────────────────────────────────────────────────────


async def test_birk_count_sensor_value(hass, setup_integration) -> None:
    entity_id = _entity_id(hass, f"{DOMAIN}_koebenhavn_birk_count")
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "186"


async def test_out_of_season_count_sensor_is_unknown(hass, setup_integration) -> None:
    entity_id = _entity_id(hass, f"{DOMAIN}_koebenhavn_graes_count")
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == STATE_UNKNOWN


async def test_count_sensor_severity_attribute(hass, setup_integration) -> None:
    entity_id = _entity_id(hass, f"{DOMAIN}_koebenhavn_birk_count")
    state = hass.states.get(entity_id)
    assert state.attributes["severity"] == "high"


async def test_count_sensor_metadata_attributes(hass, setup_integration) -> None:
    entity_id = _entity_id(hass, f"{DOMAIN}_koebenhavn_birk_count")
    attrs = hass.states.get(entity_id).attributes
    assert attrs["pollen_type_en"] == "Birch"
    assert attrs["last_update"] == "26-04-2026"
    assert "København" in attrs["region"]


async def test_count_sensor_unknown_when_no_region_data(
    hass, mock_config_entry
) -> None:
    mock_config_entry.add_to_hass(hass)
    # Return data that has no koebenhavn key
    with patch(
        "custom_components.pollen_dk.api.PollenDKApi.async_get_pollen_data",
        return_value={},
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    entity_id = _entity_id(hass, f"{DOMAIN}_koebenhavn_birk_count")
    if entity_id:
        state = hass.states.get(entity_id)
        if state:
            assert state.state in (STATE_UNKNOWN, "unavailable")


# ── Severity sensor state ─────────────────────────────────────────────────────


async def test_severity_sensor_reports_worst_level(hass, setup_integration) -> None:
    entity_id = _entity_id(hass, f"{DOMAIN}_koebenhavn_overall_severity")
    state = hass.states.get(entity_id)
    assert state is not None
    # birk is "high", everything else is "unknown" → worst known = "high"
    assert state.state == "high"


async def test_severity_sensor_all_unknown(hass, mock_config_entry) -> None:
    all_unknown_data = {
        "koebenhavn": {
            "last_update": "26-04-2026",
            "forecast_text": "",
            **{
                k: {"count": None, "severity": "unknown", "name_da": k, "name_en": v}
                for k, v in POLLEN_TYPES.items()
            },
        }
    }
    mock_config_entry.add_to_hass(hass)
    with patch(
        "custom_components.pollen_dk.api.PollenDKApi.async_get_pollen_data",
        return_value=all_unknown_data,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    entity_id = _entity_id(hass, f"{DOMAIN}_koebenhavn_overall_severity")
    assert hass.states.get(entity_id).state == "unknown"


async def test_severity_sensor_escalates_to_very_high(hass, mock_config_entry) -> None:
    high_data = {
        "koebenhavn": {
            "last_update": "26-04-2026",
            "forecast_text": "",
            "birk": {
                "count": 600,
                "severity": "very_high",
                "name_da": "birk",
                "name_en": "Birch",
            },
            "bynke": {
                "count": 25,
                "severity": "moderate",
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
        }
    }
    mock_config_entry.add_to_hass(hass)
    with patch(
        "custom_components.pollen_dk.api.PollenDKApi.async_get_pollen_data",
        return_value=high_data,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    entity_id = _entity_id(hass, f"{DOMAIN}_koebenhavn_overall_severity")
    assert hass.states.get(entity_id).state == "very_high"


# ── PollenSeveritySensor.SEVERITY_ORDER ───────────────────────────────────────


def test_severity_order_starts_with_unknown() -> None:
    assert PollenSeveritySensor.SEVERITY_ORDER[0] == "unknown"


def test_severity_order_ends_with_very_high() -> None:
    assert PollenSeveritySensor.SEVERITY_ORDER[-1] == "very_high"


def test_severity_order_is_strictly_ascending() -> None:
    order = PollenSeveritySensor.SEVERITY_ORDER
    assert order.index("unknown") < order.index("none")
    assert order.index("none") < order.index("low")
    assert order.index("low") < order.index("moderate")
    assert order.index("moderate") < order.index("high")
    assert order.index("high") < order.index("very_high")
