"""HTTP view to receive push updates from the Scrypted plugin.

Instead of the plugin maintaining a WebSocket connection to HA and using
fire_event (which requires an admin token), the plugin POSTs state updates,
entity changes, and heartbeats to this endpoint. The view validates the
shared ha_secret and fires the corresponding HA bus events internally.

Endpoint: POST /api/scrypted_an/push
Auth: Bearer ha_secret (custom, not HA auth)
"""
from __future__ import annotations

import logging
from typing import Any

from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant

from .const import (
    CONF_HA_SECRET,
    DOMAIN,
    HA_EVENT_ENTITY_CHANGE,
    HA_EVENT_HEARTBEAT,
    HA_EVENT_STATE_UPDATE,
    PUSH_API_PATH,
)

_LOGGER = logging.getLogger(__name__)


class ScryptedPushView(HomeAssistantView):
    """Receive push updates from the Scrypted plugin via REST POST.

    Supports single messages and batched messages:
      Single:  { "type": "state_update", "topic": "...", "value": "..." }
      Batch:   { "type": "batch", "items": [ ... ] }
      Rotate:  { "type": "rotate_secret", "new_secret": "..." }
    """

    url = PUSH_API_PATH
    name = "api:scrypted_an:push"
    requires_auth = False  # Custom auth via ha_secret

    async def post(self, request: web.Request) -> web.Response:
        """Handle incoming push from Scrypted plugin."""
        hass: HomeAssistant = request.app["hass"]

        # Authenticate via ha_secret
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return web.Response(status=401, text="Missing Bearer token")

        token = auth_header[7:].strip()
        entry_id = _find_entry_id_by_secret(hass, token)
        if entry_id is None:
            return web.Response(status=401, text="Invalid secret")

        try:
            data = await request.json()
        except Exception:
            return web.Response(status=400, text="Invalid JSON")

        msg_type = data.get("type", "")

        if msg_type == "rotate_secret":
            return await _handle_rotate_secret(hass, entry_id, data)
        elif msg_type == "batch":
            for item in data.get("items", []):
                _fire_bus_event(hass, item)
        else:
            _fire_bus_event(hass, data)

        return web.Response(status=200, text="ok")


def _find_entry_id_by_secret(hass: HomeAssistant, token: str) -> str | None:
    """Find the config entry ID that matches the given secret."""
    for key, value in hass.data.get(DOMAIN, {}).items():
        if (
            key.endswith("_conn")
            and isinstance(value, dict)
            and value.get("ha_secret") == token
        ):
            # key is "{entry_id}_conn" — extract entry_id
            return key[: -len("_conn")]
    return None


async def _handle_rotate_secret(
    hass: HomeAssistant, entry_id: str, data: dict[str, Any]
) -> web.Response:
    """Rotate the ha_secret for the matching config entry."""
    new_secret = data.get("new_secret", "").strip()
    if not new_secret:
        return web.Response(status=400, text="Missing new_secret")

    # Find the config entry
    entry = hass.config_entries.async_get_entry(entry_id)
    if entry is None:
        _LOGGER.error("rotate_secret: config entry %s not found", entry_id)
        return web.Response(status=404, text="Config entry not found")

    # Update config entry data with new secret
    new_data = {**entry.data, CONF_HA_SECRET: new_secret}
    hass.config_entries.async_update_entry(entry, data=new_data)

    # Update the cached connection info
    conn_key = f"{entry_id}_conn"
    conn = hass.data.get(DOMAIN, {}).get(conn_key)
    if isinstance(conn, dict):
        conn["ha_secret"] = new_secret

    _LOGGER.info("rotate_secret: secret rotated successfully for entry %s", entry_id)
    return web.Response(status=200, text="ok")


def _fire_bus_event(hass: HomeAssistant, item: dict[str, Any]) -> None:
    """Fire the corresponding HA bus event for a push item."""
    t = item.get("type", "")
    if t == "state_update":
        hass.bus.async_fire(
            HA_EVENT_STATE_UPDATE,
            {"topic": item.get("topic", ""), "value": item.get("value", "")},
        )
    elif t == "entity_change":
        hass.bus.async_fire(
            HA_EVENT_ENTITY_CHANGE,
            {"device_id": item.get("device_id", "")},
        )
    elif t == "heartbeat":
        hass.bus.async_fire(
            HA_EVENT_HEARTBEAT,
            {"ts": item.get("ts", 0)},
        )
