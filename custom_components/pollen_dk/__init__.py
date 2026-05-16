"""Pollen DK - Home Assistant integration for Astma-Allergi Danmark pollen data."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.helpers.aiohttp_client import async_get_clientsession

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

from .api import PollenDKApi
from .const import DOMAIN
from .coordinator import PollenDKCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor"]

_CARD_URL = f"/{DOMAIN}/www/pollen-dk-card.js"


async def async_setup(hass: HomeAssistant, _config: dict) -> bool:
    """Register Lovelace card resources once when the integration loads."""
    await _register_card(hass)
    return True


async def _register_card(hass: HomeAssistant) -> None:
    """Register the custom card JS file with the HA frontend (idempotent)."""
    flag = f"{DOMAIN}_card_registered"
    if hass.data.get(flag):
        return
    hass.data[flag] = True

    if hass.http is None:
        return

    www_path = Path(__file__).parent / "www"
    await hass.http.async_register_static_paths(
        [StaticPathConfig(f"/{DOMAIN}/www", www_path, cache_headers=False)]
    )
    add_extra_js_url(hass, _CARD_URL)
    _LOGGER.debug("Registered Pollen DK card at %s", _CARD_URL)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Pollen DK from a config entry."""
    session = async_get_clientsession(hass)
    api = PollenDKApi(session)
    coordinator = PollenDKCoordinator(hass, api)

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
