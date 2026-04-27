"""DataUpdateCoordinator for Pollen DK."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import PollenDKApi, PollenDKApiError
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


class PollenDKCoordinator(DataUpdateCoordinator):
    """Coordinator that fetches pollen data once per hour."""

    def __init__(self, hass: HomeAssistant, api: PollenDKApi) -> None:
        """Initialise the coordinator with HA instance and API client."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.api = api

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from the Astma-Allergi API."""
        try:
            return await self.api.async_get_pollen_data()
        except PollenDKApiError as err:
            msg = f"Error fetching pollen data: {err}"
            raise UpdateFailed(msg) from err
