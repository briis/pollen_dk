"""Pollen DK - Home Assistant integration for Astma-Allergi Danmark pollen data."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import homeassistant.helpers.config_validation as cv
from homeassistant.components.http import StaticPathConfig
from homeassistant.components.lovelace.const import DOMAIN as LOVELACE_DOMAIN
from homeassistant.components.lovelace.resources import ResourceStorageCollection
from homeassistant.helpers.aiohttp_client import async_get_clientsession

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

from .api import PollenDKApi
from .const import DOMAIN
from .coordinator import PollenDKCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor"]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

_CARD_URL = f"/{DOMAIN}/www/pollen-dk-card.js"
_STATIC_PATH_FLAG = f"{DOMAIN}_static_registered"


async def async_setup(hass: HomeAssistant, _config: dict) -> bool:
    """Register Lovelace card resources once when the integration loads."""
    await _register_card(hass)
    return True


async def _register_card(hass: HomeAssistant) -> None:
    """Register the custom card JS as a persistent Lovelace resource (idempotent)."""
    # Register the static HTTP path (in-memory, once per runtime)
    if hass.http is not None and not hass.data.get(_STATIC_PATH_FLAG):
        hass.data[_STATIC_PATH_FLAG] = True
        www_path = str(Path(__file__).parent / "www")
        await hass.http.async_register_static_paths(
            [StaticPathConfig(f"/{DOMAIN}/www", www_path, cache_headers=False)]
        )

    # Register as a persistent Lovelace resource so it survives HA restarts
    lovelace = hass.data.get(LOVELACE_DOMAIN)
    if lovelace is None:
        return

    resources = lovelace.resources
    if not isinstance(resources, ResourceStorageCollection):
        return

    # Ensure storage is loaded before inspecting items
    await resources._async_ensure_loaded()  # noqa: SLF001

    for item in resources.async_items():
        if item.get("url") == _CARD_URL:
            _LOGGER.debug("Pollen DK card already registered as Lovelace resource")
            return

    await resources.async_create_item({"res_type": "module", "url": _CARD_URL})
    _LOGGER.debug("Registered Pollen DK card at %s as Lovelace resource", _CARD_URL)


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
