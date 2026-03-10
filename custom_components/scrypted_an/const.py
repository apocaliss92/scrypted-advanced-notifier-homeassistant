"""Constants for Scrypted Advanced Notifier integration."""

DOMAIN = "scrypted_an"

CONF_SCRYPTED_URL = "scrypted_url"
CONF_HA_SECRET = "ha_secret"
CONF_SELECTED_DEVICE_IDS = "selected_device_ids"

# HA bus event names (fired by Scrypted plugin via fire_event)
HA_EVENT_STATE_UPDATE = "scrypted_an_state_update"
HA_EVENT_ENTITY_CHANGE = "scrypted_an_entity_change"
HA_EVENT_HEARTBEAT = "scrypted_an_heartbeat"

# Heartbeat timeout: if no heartbeat received in this time, mark entities unavailable
HEARTBEAT_TIMEOUT_S = 90  # plugin sends every 30s, so 3 missed = unavailable

# HTTP endpoints (relative to scrypted_url + /endpoint/@apocaliss92/scrypted-advanced-notifier)
ENDPOINT_BASE = "/endpoint/@apocaliss92/scrypted-advanced-notifier"
ENDPOINT_HA_DEVICES = f"{ENDPOINT_BASE}/public/ha/devices"
ENDPOINT_HA_ENTITIES = f"{ENDPOINT_BASE}/public/ha/entities"
ENDPOINT_HA_COMMAND = f"{ENDPOINT_BASE}/public/ha/command"
ENDPOINT_HA_IMAGE = f"{ENDPOINT_BASE}/public/ha/image"
