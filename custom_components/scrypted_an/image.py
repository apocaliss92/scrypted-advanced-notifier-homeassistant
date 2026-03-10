"""Image platform for Scrypted Advanced Notifier."""
from __future__ import annotations

from datetime import datetime
import logging

import aiohttp
from homeassistant.components.image import ImageEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
import homeassistant.util.dt as dt_util

from .const import DOMAIN, ENDPOINT_HA_IMAGE
from .base_entity import ScryptedBaseEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    manager = hass.data[DOMAIN][entry.entry_id]
    manager.register_platform("image", async_add_entities)


class ScryptedImage(ScryptedBaseEntity, ImageEntity):
    """An image entity from Scrypted (shows last detection snapshot).

    Images are fetched on-demand from the plugin's REST endpoint
    instead of being pushed via base64 events.
    """

    _attr_content_type = "image/jpeg"

    def __init__(self, entry_id, device_id, dev, component_key, cmp_config, entity_manager) -> None:
        ScryptedBaseEntity.__init__(self, entry_id, device_id, dev, component_key, cmp_config, entity_manager)
        ImageEntity.__init__(self, entity_manager.hass)
        self._image_topic: str | None = cmp_config.get("image_topic")
        self._image_last_updated: datetime | None = None

        # Subscribe to lightweight update signal (not base64 data)
        if self._image_topic:
            self._entity_manager.subscribe_topic(self._image_topic, self._on_image_signal)

    @property
    def image_last_updated(self) -> datetime | None:
        return self._image_last_updated

    async def async_image(self) -> bytes | None:
        """Fetch image on-demand from plugin REST endpoint."""
        if not self._image_topic:
            _LOGGER.warning("async_image called but no image_topic for %s", self._attr_unique_id)
            return None

        conn = self.hass.data[DOMAIN].get(f"{self._entry_id}_conn")
        if not conn:
            _LOGGER.warning("No connection info for image fetch")
            return None

        scrypted_url = conn["scrypted_url"]
        ha_secret = conn["ha_secret"]
        url = f"{scrypted_url}{ENDPOINT_HA_IMAGE}?topic={self._image_topic}"
        ha_origin = str(self.hass.config.external_url or self.hass.config.internal_url or "")
        headers = {"Authorization": f"Bearer {ha_secret}", "Origin": ha_origin}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, headers=headers, timeout=aiohttp.ClientTimeout(total=10), ssl=False
                ) as resp:
                    if resp.status == 200:
                        data = await resp.read()
                        _LOGGER.debug("Image fetched OK for topic %s: %d bytes", self._image_topic, len(data))
                        return data
                    _LOGGER.warning("Image fetch HTTP %s for topic %s url %s", resp.status, self._image_topic, url)
        except Exception as e:
            _LOGGER.warning("Error fetching image for topic %s: %s", self._image_topic, e)

        return None

    def _on_image_signal(self, value: str) -> None:
        """Lightweight signal that a new image is available."""
        if not value:
            return
        _LOGGER.debug("Image signal received for %s: %s", self._image_topic, value[:50] if value else "")
        self._image_last_updated = dt_util.utcnow()
        self.schedule_update_ha_state()
