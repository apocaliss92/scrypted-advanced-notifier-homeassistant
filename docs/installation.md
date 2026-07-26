# Installation and configuration

Migrated from the repository `README.md`, which HACS renders and which stays the
canonical copy. Change it there first.

## Installation via HACS

1. Add this repository as a custom HACS integration
2. Install **Scrypted Advanced Notifier**
3. Restart Home Assistant
4. Go to **Settings → Integrations → Add Integration** and search for *Scrypted Advanced Notifier*

## Configuration

1. Enter your Scrypted URL (e.g. `http://scrypted.local:11080`)
2. Enter the HA Secret from the Advanced Notifier plugin settings
3. Select which cameras to import

## Requirements

- [Scrypted](https://scrypted.app/) with the Advanced Notifier plugin installed
- Home Assistant 2024.1.0 or newer

## Supported platforms

`binary_sensor`, `sensor`, `switch`, `button`, `select`, `image`, `camera`
