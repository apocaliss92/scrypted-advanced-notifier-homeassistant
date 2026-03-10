"""Scrypted Advanced Notifier integration."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant

from .const import (
    CONF_HA_SECRET,
    CONF_SCRYPTED_URL,
    CONF_SELECTED_DEVICE_IDS,
    DOMAIN,
    ENDPOINT_HA_COMMAND,
    ENDPOINT_HA_ENTITIES,
    HA_EVENT_ENTITY_CHANGE,
    HA_EVENT_STATE_UPDATE,
)
from .entity_manager import EntityManager

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["binary_sensor", "sensor", "switch", "button", "select", "image", "camera"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Scrypted Advanced Notifier from a config entry."""
    scrypted_url = entry.data[CONF_SCRYPTED_URL].rstrip("/")
    ha_secret = entry.data[CONF_HA_SECRET]
    selected_ids: list[str] = entry.data.get(CONF_SELECTED_DEVICE_IDS, [])

    manager = EntityManager(hass, entry.entry_id)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = manager

    # Store connection info for command sending
    hass.data[DOMAIN][f"{entry.entry_id}_conn"] = {
        "scrypted_url": scrypted_url,
        "ha_secret": ha_secret,
    }

    # Register bus listeners BEFORE fetching entities to avoid missing early push events
    async def _on_state_update(event: Event) -> None:
        topic = event.data.get("topic", "")
        value = event.data.get("value", "")
        manager.update_state(topic, value)

    async def _on_entity_change(event: Event) -> None:
        device_id = event.data.get("device_id", "")
        cmps = event.data.get("cmps")
        dev = event.data.get("dev")
        manager.apply_entity_diff(device_id=device_id, cmps=cmps, dev=dev)

    unsub_state = hass.bus.async_listen(HA_EVENT_STATE_UPDATE, _on_state_update)
    unsub_entity = hass.bus.async_listen(HA_EVENT_ENTITY_CHANGE, _on_entity_change)
    hass.data[DOMAIN][f"{entry.entry_id}_unsub"] = [unsub_state, unsub_entity]

    # Set up platforms, then fetch entities from plugin REST endpoint and create them directly
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _LOGGER.info("Fetching entities for selected IDs: %s", selected_ids)
    devices, states = await _fetch_entities(scrypted_url, ha_secret, selected_ids, hass)
    _LOGGER.info("Fetched %d devices and %d initial states", len(devices), len(states))
    for device in devices:
        device_id = device.get("device_id", "")
        cmps = device.get("cmps", {})
        _LOGGER.info("Creating device %s with %d components: %s", device_id, len(cmps), list(cmps.keys()))
        manager.apply_entity_diff(
            device_id=device_id,
            cmps=cmps,
            dev=device.get("dev"),
        )
    # Apply initial states so entities show correct values right away
    for state in states:
        manager.update_state(state.get("topic", ""), state.get("value", ""))

    # Listen for config entry updates (OptionsFlow device selection changes)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle config entry updates (e.g. device selection changed in OptionsFlow)."""
    _LOGGER.info("Config entry updated — processing device selection changes")
    manager: EntityManager | None = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if not manager:
        _LOGGER.warning("No EntityManager found for entry %s", entry.entry_id)
        return

    new_selected: list[str] = entry.data.get(CONF_SELECTED_DEVICE_IDS, [])
    new_set = set(new_selected)

    # Remove entities for devices that are no longer selected
    current_device_ids = list(manager.get_device_ids())
    _LOGGER.info("Current device IDs in manager: %s", current_device_ids)
    _LOGGER.info("New selected device IDs: %s", new_selected)
    for device_id in current_device_ids:
        if device_id not in new_set:
            _LOGGER.info("Device %s deselected — removing entities", device_id)
            manager.apply_entity_diff(device_id=device_id, cmps={}, dev={})

    # Fetch and create entities for newly selected devices
    scrypted_url = entry.data[CONF_SCRYPTED_URL].rstrip("/")
    ha_secret = entry.data[CONF_HA_SECRET]
    devices, states = await _fetch_entities(scrypted_url, ha_secret, new_selected, hass)
    _LOGGER.info("Fetched %d devices for update", len(devices))
    for device in devices:
        device_id = device.get("device_id", "")
        if device_id not in current_device_ids:
            _LOGGER.info("Device %s newly selected — creating entities", device_id)
            manager.apply_entity_diff(
                device_id=device_id,
                cmps=device.get("cmps"),
                dev=device.get("dev"),
            )
    # Apply initial states for new entities
    for state in states:
        manager.update_state(state.get("topic", ""), state.get("value", ""))


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unsubscribe from HA bus events
    for unsub in hass.data[DOMAIN].pop(f"{entry.entry_id}_unsub", []):
        unsub()

    hass.data[DOMAIN].pop(f"{entry.entry_id}_conn", None)

    manager: EntityManager = hass.data[DOMAIN].pop(entry.entry_id, None)
    if manager:
        await manager.async_unload()

    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _fetch_entities(
    scrypted_url: str, ha_secret: str, selected_ids: list[str], hass: HomeAssistant
) -> tuple[list[dict], list[dict]]:
    """Fetch initial entity list and states from plugin REST endpoint.

    Returns (devices, states) where states is a list of {topic, value} dicts.
    """
    url = f"{scrypted_url}{ENDPOINT_HA_ENTITIES}"
    if selected_ids:
        url += "?device_ids=" + ",".join(selected_ids)
    ha_origin = str(hass.config.external_url or hass.config.internal_url or "")
    headers = {"Authorization": f"Bearer {ha_secret}", "Origin": ha_origin}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url, headers=headers, timeout=aiohttp.ClientTimeout(total=15), ssl=False
            ) as resp:
                if resp.status != 200:
                    _LOGGER.error("Failed to fetch entities: HTTP %s", resp.status)
                    return [], []
                data = await resp.json()
                return data.get("devices", []), data.get("states", [])
    except Exception as e:
        _LOGGER.error("Error fetching entities: %s", e)
        return [], []


async def _send_command_to_plugin(
    scrypted_url: str, ha_secret: str, ha_origin: str, topic: str, value: str
) -> None:
    """POST a command to the plugin's /public/ha/command REST endpoint."""
    url = f"{scrypted_url}{ENDPOINT_HA_COMMAND}"
    headers = {"Authorization": f"Bearer {ha_secret}", "Origin": ha_origin, "Content-Type": "application/json"}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url, json={"topic": topic, "value": value}, headers=headers, timeout=aiohttp.ClientTimeout(total=10), ssl=False
            ) as resp:
                if resp.status != 200:
                    _LOGGER.warning("Command POST failed: HTTP %s", resp.status)
    except Exception as e:
        _LOGGER.warning("Failed to send command to plugin: %s", e)


def send_command(hass: HomeAssistant, entry_id: str, topic: str, value: str) -> None:
    """Send a command to the plugin via REST POST /public/ha/command."""
    conn = hass.data[DOMAIN].get(f"{entry_id}_conn")
    if not conn:
        return
    ha_origin = str(hass.config.external_url or hass.config.internal_url or "")
    hass.async_create_task(
        _send_command_to_plugin(conn["scrypted_url"], conn["ha_secret"], ha_origin, topic, value)
    )


def build_entity(
    hass: HomeAssistant,
    entry_id: str,
    device_id: str,
    dev: dict,
    component_key: str,
    cmp_config: dict,
    entity_manager: EntityManager,
) -> Any | None:
    """Factory: instantiate the right HA entity class from a component config."""
    platform = cmp_config.get("platform")

    if platform == "binary_sensor":
        from .binary_sensor import ScryptedBinarySensor
        return ScryptedBinarySensor(entry_id, device_id, dev, component_key, cmp_config, entity_manager)
    if platform == "sensor":
        from .sensor import ScryptedSensor
        return ScryptedSensor(entry_id, device_id, dev, component_key, cmp_config, entity_manager)
    if platform == "switch":
        from .switch import ScryptedSwitch
        return ScryptedSwitch(entry_id, device_id, dev, component_key, cmp_config, entity_manager)
    if platform == "button":
        from .button import ScryptedButton
        return ScryptedButton(entry_id, device_id, dev, component_key, cmp_config, entity_manager)
    if platform == "select":
        from .select import ScryptedSelect
        return ScryptedSelect(entry_id, device_id, dev, component_key, cmp_config, entity_manager)
    if platform == "image":
        from .image import ScryptedImage
        return ScryptedImage(entry_id, device_id, dev, component_key, cmp_config, entity_manager)
    if platform == "camera":
        from .camera import ScryptedCamera
        return ScryptedCamera(entry_id, device_id, dev, component_key, cmp_config, entity_manager)

    _LOGGER.debug("Unknown platform '%s' for component %s", platform, component_key)
    return None
