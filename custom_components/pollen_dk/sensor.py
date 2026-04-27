"""Sensor platform for Pollen DK integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, ClassVar

from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
)
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTRIBUTION,
    CONF_REGION,
    DOMAIN,
    POLLEN_ICONS,
    POLLEN_TYPES,
    REGION_BOTH,
    REGION_KOEBENHAVN,
    REGION_VIBORG,
    REGIONS,
    SEVERITY_ICONS,
)
from .coordinator import PollenDKCoordinator

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Pollen DK sensor entities."""
    coordinator: PollenDKCoordinator = hass.data[DOMAIN][entry.entry_id]
    selected_region = entry.data[CONF_REGION]

    regions_to_use = (
        [REGION_KOEBENHAVN, REGION_VIBORG]
        if selected_region == REGION_BOTH
        else [selected_region]
    )

    entities: list[SensorEntity] = []
    for region_key in regions_to_use:
        entities.extend(
            PollenCountSensor(coordinator, region_key, pollen_key)
            for pollen_key in POLLEN_TYPES
        )
        entities.append(PollenSeveritySensor(coordinator, region_key))

    async_add_entities(entities)


class PollenBaseSensor(CoordinatorEntity[PollenDKCoordinator], SensorEntity):
    """Base class for Pollen DK sensors."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: PollenDKCoordinator,
        region_key: str,
    ) -> None:
        """Initialise the base sensor for a given region."""
        super().__init__(coordinator)
        self._region_key = region_key
        region_name = REGIONS[region_key]

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, region_key)},
            name=f"Pollen DK - {region_name}",
            manufacturer="Astma-Allergi Danmark",
            model="Pollenmålestation",
            configuration_url="https://www.astma-allergi.dk/dagenspollental",
        )

    @property
    def _region_data(self) -> dict[str, Any] | None:
        """Return data for this sensor's region."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get(self._region_key)


class PollenCountSensor(PollenBaseSensor):
    """Sensor reporting the raw pollen grain count (pollen/m³) for one type."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "pollen/m³"

    def __init__(
        self,
        coordinator: PollenDKCoordinator,
        region_key: str,
        pollen_key: str,
    ) -> None:
        """Initialise the count sensor for a specific pollen type and region."""
        super().__init__(coordinator, region_key)
        self._pollen_key = pollen_key

        region_name = REGIONS[region_key]
        pollen_name = POLLEN_TYPES[pollen_key]

        self._attr_unique_id = f"{DOMAIN}_{region_key}_{pollen_key}_count"
        self._attr_name = f"{pollen_name} ({region_name})"
        self._attr_icon = POLLEN_ICONS.get(pollen_key, "mdi:flower-pollen")

    @property
    def native_value(self) -> int | None:
        """Return the pollen count."""
        region_data = self._region_data
        if region_data is None:
            return None
        pollen_data = region_data.get(self._pollen_key)
        if pollen_data is None:
            return None
        return pollen_data.get("count")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return severity level and metadata."""
        region_data = self._region_data
        if region_data is None:
            return {}
        pollen_data = region_data.get(self._pollen_key, {})
        return {
            "severity": pollen_data.get("severity", "unknown"),
            "pollen_type_da": POLLEN_TYPES[self._pollen_key],
            "pollen_type_en": pollen_data.get("name_en", ""),
            "last_update": region_data.get("last_update", ""),
            "region": REGIONS[self._region_key],
            "attribution": ATTRIBUTION,
        }


class PollenSeveritySensor(PollenBaseSensor):
    """Sensor reporting the overall worst severity level for a region."""

    _attr_translation_key = "pollen_severity"

    SEVERITY_ORDER: ClassVar[list[str]] = [
        "unknown",
        "none",
        "low",
        "moderate",
        "high",
        "very_high",
    ]

    def __init__(
        self,
        coordinator: PollenDKCoordinator,
        region_key: str,
    ) -> None:
        """Initialise the overall severity sensor for a region."""
        super().__init__(coordinator, region_key)
        region_name = REGIONS[region_key]

        self._attr_unique_id = f"{DOMAIN}_{region_key}_overall_severity"
        self._attr_name = f"Pollenvarsel ({region_name})"
        self._attr_icon = "mdi:flower-pollen"

    @property
    def native_value(self) -> str | None:
        """Return the worst severity level among all active pollen types."""
        region_data = self._region_data
        if region_data is None:
            return None

        worst_idx = 0
        for pollen_key in POLLEN_TYPES:
            pollen_data = region_data.get(pollen_key, {})
            severity = pollen_data.get("severity", "unknown")
            try:
                idx = self.SEVERITY_ORDER.index(severity)
            except ValueError:
                idx = 0
            worst_idx = max(worst_idx, idx)

        return self.SEVERITY_ORDER[worst_idx]

    @property
    def icon(self) -> str:
        """Return icon based on severity."""
        return SEVERITY_ICONS.get(self.native_value or "unknown", "mdi:flower-pollen")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return per-pollen-type severities and the forecast text."""
        region_data = self._region_data
        if region_data is None:
            return {}

        severities = {}
        for pollen_key in POLLEN_TYPES:
            pollen_data = region_data.get(pollen_key, {})
            count = pollen_data.get("count")
            if count is not None:
                severities[POLLEN_TYPES[pollen_key]] = {
                    "count": count,
                    "severity": pollen_data.get("severity", "unknown"),
                }

        return {
            "pollen_levels": severities,
            "forecast": region_data.get("forecast_text", ""),
            "last_update": region_data.get("last_update", ""),
            "region": REGIONS[self._region_key],
            "attribution": ATTRIBUTION,
        }
