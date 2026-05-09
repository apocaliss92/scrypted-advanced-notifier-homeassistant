"""Bus listener for HA Companion notification actions.

Catches `mobile_app_notification_action` events whose `action` starts with
`scrypted_an_` and forwards them to the plugin via /public/ha/command.

For snooze actions the topic + payload mirror exactly what the legacy YAML
automation `scrypted_advanced_notifier_snooze_action` publishes via mqtt.publish:
the plugin's MQTT-shaped subscriber (HaEventClient.routeCommand) is the same on
both paths, so users on the native component path no longer need that automation
and the underlying snooze handling stays untouched.
"""
from __future__ import annotations

import json
import logging
from typing import Callable

from homeassistant.core import Event, HomeAssistant, callback

_LOGGER = logging.getLogger(__name__)

EVENT_TYPE = "mobile_app_notification_action"
ACTION_PREFIX = "scrypted_an_"
SNOOZE_PREFIX = "scrypted_an_snooze_"


def _parse_snooze_action(action: str) -> dict[str, str] | None:
    """Mirror of haSnoozeAutomation parsing in the plugin's utils.ts.

    Format: scrypted_an_snooze_{cameraId}_{notifierId}_{snoozeTime}_{snoozeId}
    where snoozeId itself may contain underscores.
    """
    suffix = action[len(SNOOZE_PREFIX):]
    parts = suffix.split("_")
    if len(parts) < 4:
        return None
    return {
        "cameraId": parts[0],
        "notifierId": parts[1],
        "snoozeTime": parts[2],
        "snoozeId": "_".join(parts[3:]),
    }


def async_setup_action_listener(
    hass: HomeAssistant, entry_id: str
) -> Callable[[], None]:
    """Register the bus listener; returns the unsub callable."""
    # Deferred to avoid a circular import at package load time
    from . import send_command

    @callback
    def _on_action(event: Event) -> None:
        action = event.data.get("action")
        if not isinstance(action, str) or not action.startswith(ACTION_PREFIX):
            return

        if action.startswith(SNOOZE_PREFIX):
            parsed = _parse_snooze_action(action)
            if parsed is None:
                _LOGGER.warning("Malformed snooze action id: %s", action)
                return
            topic = (
                f"scrypted-an/scrypted-an-{parsed['notifierId']}/snooze/set"
            )
            value = json.dumps(
                {
                    "snoozeId": parsed["snoozeId"],
                    "cameraId": parsed["cameraId"],
                    "snoozeTime": parsed["snoozeTime"],
                }
            )
            send_command(hass, entry_id, topic, value)
            _LOGGER.debug("Routed snooze action: topic=%s value=%s", topic, value)
            return

        _LOGGER.debug("Unhandled scrypted_an_ action: %s", action)

    return hass.bus.async_listen(EVENT_TYPE, _on_action)
