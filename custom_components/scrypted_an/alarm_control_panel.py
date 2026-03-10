"""Alarm control panel platform for Scrypted Advanced Notifier."""
from __future__ import annotations

import logging

from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntity,
    AlarmControlPanelEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .base_entity import ScryptedBaseEntity
from . import send_command

_LOGGER = logging.getLogger(__name__)

# Map feature strings from Scrypted to HA feature flags
_FEATURE_MAP = {
    "arm_away": AlarmControlPanelEntityFeature.ARM_AWAY,
    "arm_home": AlarmControlPanelEntityFeature.ARM_HOME,
    "arm_night": AlarmControlPanelEntityFeature.ARM_NIGHT,
    "trigger": AlarmControlPanelEntityFeature.TRIGGER,
}

# Map HA alarm states from Scrypted state topic values
_STATE_MAP = {
    "armed_away": "armed_away",
    "armed_home": "armed_home",
    "armed_night": "armed_night",
    "disarmed": "disarmed",
    "triggered": "triggered",
    "arming": "arming",
    "pending": "pending",
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    manager = hass.data[DOMAIN][entry.entry_id]
    manager.register_platform("alarm_control_panel", async_add_entities)


class ScryptedAlarmControlPanel(ScryptedBaseEntity, AlarmControlPanelEntity):
    """An alarm control panel entity from Scrypted."""

    _attr_code_arm_required = False

    @property
    def supported_features(self) -> AlarmControlPanelEntityFeature:
        features = AlarmControlPanelEntityFeature(0)
        for feat_str in self._cmp_config.get("supported_features", []):
            if flag := _FEATURE_MAP.get(feat_str):
                features |= flag
        return features

    @property
    def state(self) -> str | None:
        if self._state_value is None:
            return None
        return _STATE_MAP.get(self._state_value.lower(), self._state_value)

    async def async_alarm_arm_away(self, code: str | None = None) -> None:
        cmd_topic = self._cmp_config.get("cmd_t") or self._cmp_config.get("command_topic", "")
        payload = self._cmp_config.get("payload_arm_away", "ARM_AWAY")
        send_command(self.hass, self._entry_id, cmd_topic, payload)

    async def async_alarm_arm_home(self, code: str | None = None) -> None:
        cmd_topic = self._cmp_config.get("cmd_t") or self._cmp_config.get("command_topic", "")
        payload = self._cmp_config.get("payload_arm_home", "ARM_HOME")
        send_command(self.hass, self._entry_id, cmd_topic, payload)

    async def async_alarm_arm_night(self, code: str | None = None) -> None:
        cmd_topic = self._cmp_config.get("cmd_t") or self._cmp_config.get("command_topic", "")
        payload = self._cmp_config.get("payload_arm_night", "ARM_NIGHT")
        send_command(self.hass, self._entry_id, cmd_topic, payload)

    async def async_alarm_disarm(self, code: str | None = None) -> None:
        cmd_topic = self._cmp_config.get("cmd_t") or self._cmp_config.get("command_topic", "")
        payload = self._cmp_config.get("payload_disarm", "DISARM")
        send_command(self.hass, self._entry_id, cmd_topic, payload)

    async def async_alarm_trigger(self, code: str | None = None) -> None:
        cmd_topic = self._cmp_config.get("cmd_t") or self._cmp_config.get("command_topic", "")
        payload = self._cmp_config.get("payload_trigger", "TRIGGER")
        send_command(self.hass, self._entry_id, cmd_topic, payload)
