"""Camera platform for Scrypted Advanced Notifier (stream destinations)."""
from __future__ import annotations

import logging

import aiohttp
from homeassistant.components.camera import Camera
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, ENDPOINT_HA_IMAGE
from .base_entity import ScryptedBaseEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    manager = hass.data[DOMAIN][entry.entry_id]
    manager.register_platform("camera", async_add_entities)


class ScryptedCamera(ScryptedBaseEntity, Camera):
    """A camera entity exposing a Scrypted stream destination."""

    def __init__(self, *args, **kwargs) -> None:
        ScryptedBaseEntity.__init__(self, *args, **kwargs)
        Camera.__init__(self)

    @property
    def is_streaming(self) -> bool:
        return True

    async def stream_source(self) -> str | None:
        return self._cmp_config.get("rtsp_url") or self._cmp_config.get("stream_source")

    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        """Fetch snapshot from plugin's /public/ha/image endpoint using device_id."""
        conn = self.hass.data[DOMAIN].get(f"{self._entry_id}_conn")
        if not conn:
            return None

        scrypted_url = conn["scrypted_url"]
        ha_secret = conn["ha_secret"]
        url = f"{scrypted_url}{ENDPOINT_HA_IMAGE}?device_id={self._device_id}"
        ha_origin = str(self.hass.config.external_url or self.hass.config.internal_url or "")
        headers = {"Authorization": f"Bearer {ha_secret}", "Origin": ha_origin}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, headers=headers, timeout=aiohttp.ClientTimeout(total=10), ssl=False
                ) as resp:
                    if resp.status == 200:
                        return await resp.read()
                    _LOGGER.debug("Camera snapshot fetch returned HTTP %s for %s", resp.status, self._device_id)
        except Exception as e:
            _LOGGER.warning("Failed to fetch camera snapshot for %s: %s", self._device_id, e)
        return None
