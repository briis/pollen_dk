"""Config flow for Pollen DK integration."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import PollenDKApi, PollenDKApiError
from .const import CONF_REGION, DOMAIN, REGION_BOTH, REGIONS

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_REGION, default=REGION_BOTH): vol.In(REGIONS),
    }
)


async def validate_connection(hass: HomeAssistant) -> None:
    """Validate that the API is reachable."""
    session = async_get_clientsession(hass)
    api = PollenDKApi(session)
    await api.async_get_pollen_data()


class PollenDKConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Pollen DK."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial setup step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                await validate_connection(self.hass)
            except PollenDKApiError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error during setup")
                errors["base"] = "unknown"
            else:
                region = user_input[CONF_REGION]
                await self.async_set_unique_id(f"pollen_dk_{region}")
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"Pollen DK – {REGIONS[region]}",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
            description_placeholders={
                "api_url": "astma-allergi.dk",
            },
        )
