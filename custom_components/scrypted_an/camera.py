"""Camera platform for Scrypted Advanced Notifier (stream destinations)."""
from __future__ import annotations

import logging

import aiohttp
from homeassistant.components.camera import Camera, CameraEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, ENDPOINT_HA_SNAPSHOT
from .base_entity import ScryptedBaseEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    manager = hass.data[DOMAIN][entry.entry_id]
    manager.register_platform("camera", async_add_entities)


class ScryptedCamera(ScryptedBaseEntity, Camera):
    """A camera entity exposing a Scrypted stream destination."""

    _attr_supported_features = CameraEntityFeature.STREAM

    def __init__(self, *args, **kwargs) -> None:
        ScryptedBaseEntity.__init__(self, *args, **kwargs)
        Camera.__init__(self)

    @property
    def is_streaming(self) -> bool:
        """Stream is on-demand only, not permanently connected."""
        return False

    async def stream_source(self) -> str | None:
        """Return RTSP URL only when HA requests the stream (on-demand)."""
        return self._cmp_config.get("rtsp_url") or self._cmp_config.get("stream_source")

    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        """Take a live snapshot via the plugin's /public/ha/snapshot endpoint."""
        conn = self.hass.data[DOMAIN].get(f"{self._entry_id}_conn")
        if not conn:
            return None

        scrypted_url = conn["scrypted_url"]
        ha_secret = conn["ha_secret"]
        url = f"{scrypted_url}{ENDPOINT_HA_SNAPSHOT}?device_id={self._device_id}"
        ha_origin = str(self.hass.config.external_url or self.hass.config.internal_url or "")
        headers = {"Authorization": f"Bearer {ha_secret}", "Origin": ha_origin}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, headers=headers, timeout=aiohttp.ClientTimeout(total=15), ssl=False
                ) as resp:
                    if resp.status == 200:
                        return await resp.read()
                    _LOGGER.debug("Camera snapshot returned HTTP %s for %s", resp.status, self._device_id)
        except Exception as e:
            _LOGGER.warning("Failed to fetch camera snapshot for %s: %s", self._device_id, e)
        return None
