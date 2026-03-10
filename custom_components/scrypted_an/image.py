"""Image platform for Scrypted Advanced Notifier."""
from __future__ import annotations

import base64
from datetime import datetime
import logging

from homeassistant.components.image import ImageEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
import homeassistant.util.dt as dt_util

from .const import DOMAIN
from .base_entity import ScryptedBaseEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    manager = hass.data[DOMAIN][entry.entry_id]
    manager.register_platform("image", async_add_entities)


class ScryptedImage(ScryptedBaseEntity, ImageEntity):
    """An image entity from Scrypted (shows last detection snapshot).

    Scrypted publishes base64-encoded JPEG data to the image_topic.
    """

    _attr_content_type = "image/jpeg"

    def __init__(self, entry_id, device_id, dev, component_key, cmp_config, entity_manager) -> None:
        ScryptedBaseEntity.__init__(self, entry_id, device_id, dev, component_key, cmp_config, entity_manager)
        ImageEntity.__init__(self, entity_manager.hass)
        self._image_bytes: bytes | None = None
        self._image_last_updated: datetime | None = None

        # Images are published to image_topic (not state_topic)
        image_topic: str | None = self._cmp_config.get("image_topic")
        if image_topic:
            self._entity_manager.subscribe_topic(image_topic, self._on_image_update)

    @property
    def image_last_updated(self) -> datetime | None:
        return self._image_last_updated

    async def async_image(self) -> bytes | None:
        return self._image_bytes

    def _on_image_update(self, value: str) -> None:
        """State update carries base64-encoded JPEG image data."""
        if not value:
            return
        try:
            self._image_bytes = base64.b64decode(value)
            self._image_last_updated = dt_util.utcnow()
            self.schedule_update_ha_state()
        except Exception as e:
            _LOGGER.debug("Failed to decode image data: %s", e)
