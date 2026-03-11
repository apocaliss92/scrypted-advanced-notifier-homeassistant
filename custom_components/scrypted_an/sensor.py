"""Sensor platform for Scrypted Advanced Notifier."""
from __future__ import annotations

from datetime import datetime

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
import homeassistant.util.dt as dt_util

from .const import DOMAIN
from .base_entity import ScryptedBaseEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    manager = hass.data[DOMAIN][entry.entry_id]
    manager.register_platform("sensor", async_add_entities)


class ScryptedSensor(ScryptedBaseEntity, SensorEntity):
    """A sensor entity from Scrypted."""

    @property
    def native_value(self) -> str | datetime | None:
        if self._state_value is None:
            return None
        # Timestamp device class requires a datetime object, not a string
        if self.device_class == SensorDeviceClass.TIMESTAMP:
            try:
                return dt_util.parse_datetime(self._state_value)
            except (ValueError, TypeError):
                return None
        return self._state_value

    @property
    def device_class(self) -> str | None:
        return self._cmp_config.get("dev_cla") or self._cmp_config.get("device_class")

    @property
    def native_unit_of_measurement(self) -> str | None:
        return self._cmp_config.get("unit_of_meas") or self._cmp_config.get("unit_of_measurement")

    @property
    def state_class(self) -> str | None:
        return self._cmp_config.get("stat_cla") or self._cmp_config.get("state_class")

    @property
    def suggested_display_precision(self) -> int | None:
        val = self._cmp_config.get("suggested_display_precision")
        return int(val) if val is not None else None
