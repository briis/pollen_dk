"""Tests for the PollenDK config flow."""

from __future__ import annotations

from unittest.mock import patch

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.pollen_dk.api import PollenDKApiError
from custom_components.pollen_dk.const import (
    CONF_REGION,
    DOMAIN,
    REGION_KOEBENHAVN,
    REGION_VIBORG,
)


async def test_form_shown_on_init(hass) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"
    assert not result["errors"]


async def test_successful_setup(hass) -> None:
    with patch("custom_components.pollen_dk.config_flow.validate_connection"):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_REGION: REGION_KOEBENHAVN},
        )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "Pollen DK - København (Østdanmark)"
    assert result["data"] == {CONF_REGION: REGION_KOEBENHAVN}


async def test_successful_setup_viborg(hass) -> None:
    with patch("custom_components.pollen_dk.config_flow.validate_connection"):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_REGION: REGION_VIBORG},
        )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_REGION: REGION_VIBORG}


async def test_cannot_connect_shows_error(hass) -> None:
    with patch(
        "custom_components.pollen_dk.config_flow.validate_connection",
        side_effect=PollenDKApiError("connection failed"),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_REGION: REGION_KOEBENHAVN},
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_unexpected_error_shows_error(hass) -> None:
    with patch(
        "custom_components.pollen_dk.config_flow.validate_connection",
        side_effect=RuntimeError("unexpected"),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_REGION: REGION_KOEBENHAVN},
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "unknown"}


async def test_already_configured_aborts(hass) -> None:
    existing = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_REGION: REGION_KOEBENHAVN},
        unique_id=f"pollen_dk_{REGION_KOEBENHAVN}",
    )
    existing.add_to_hass(hass)

    with patch("custom_components.pollen_dk.config_flow.validate_connection"):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_REGION: REGION_KOEBENHAVN},
        )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_different_regions_can_coexist(hass) -> None:
    existing = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_REGION: REGION_KOEBENHAVN},
        unique_id=f"pollen_dk_{REGION_KOEBENHAVN}",
    )
    existing.add_to_hass(hass)

    with patch("custom_components.pollen_dk.config_flow.validate_connection"):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_REGION: REGION_VIBORG},
        )

    assert result["type"] == FlowResultType.CREATE_ENTRY
