# Architecture

Migrated from `CLAUDE.md`, which remains in the repository root as the guidance
file agents read. Change it there first; this page mirrors it.

## Communication model

The Scrypted plugin connects **outbound** to HA's native WebSocket API
(`/api/websocket`) and fires two custom HA events:

- `scrypted_an_state_update` — `{ topic, value }` — entity state change
- `scrypted_an_entity_change` — `{ device_id, cmps, dev }` — entity structure change

HA sends commands **back** to Scrypted via REST
`POST {scrypted_url}/endpoint/@apocaliss92/scrypted-advanced-notifier/public/ha/command`
with `{ topic, value }`.

## Setup flow

1. **Config flow** (`config_flow.py`): 2 steps — enter URL+secret →
   `GET /public/ha/devices` → multi-select cameras
2. **`async_setup_entry`** (`__init__.py`): fetches initial entities via
   `GET /public/ha/entities?device_ids=...`, registers HA bus listeners, stores
   conn info for command sending
3. **`EntityManager`** (`entity_manager.py`): manages entity lifecycle
   (add/remove/update) in response to bus events

## Entity lifecycle

`EntityManager.apply_entity_diff(device_id, cmps, dev)` is the central mutation
point:

- `cmps` is a dict of `component_key → config` (same structure as MQTT
  autodiscovery `cmps`)
- New keys → instantiate via `build_entity()` factory in `__init__.py` →
  `async_add_entities()`
- Removed keys → `entity.async_remove()`
- Changed keys → `entity.update_config(new_config)`

## State updates

`EntityManager.subscribe_topic(topic, cb)` registers a callback.
`update_state(topic, value)` fans out to all subscribers for that topic. Each
`ScryptedBaseEntity` subscribes its `stat_t`/`state_topic` from `cmp_config`
during `__init__`.

## Entity base class (`base_entity.py`)

`ScryptedBaseEntity` reads `cmp_config` keys using MQTT autodiscovery short-form
names (`stat_t`, `cmd_t`, `stat_t`, etc.) since the plugin reuses that payload
structure. Command-capable entities (`switch`, `button`, `select`) call
`send_command(hass, entry_id, topic, value)` from `__init__.py`.

## REST endpoint paths (on the Scrypted plugin)

All under `/endpoint/@apocaliss92/scrypted-advanced-notifier/public/ha/`:

- `GET /devices` — list of available devices (config flow step 2)
- `GET /entities?device_ids=...` — filtered entity list with `cmps`/`dev` payloads
- `POST /command` — send command `{ topic, value }` to plugin

Auth: `Authorization: Bearer {ha_secret}` + `Origin` header matching the plugin's
allowed origins.
