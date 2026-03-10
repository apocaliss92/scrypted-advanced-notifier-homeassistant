# Scrypted Advanced Notifier — Home Assistant Integration

Custom integration for [Home Assistant](https://www.home-assistant.io/) that connects to the [Scrypted Advanced Notifier](https://github.com/apocaliss92/scrypted-advanced-notifier) plugin.

## Features

- Automatic entity discovery from Scrypted cameras
- Real-time state updates via Home Assistant WebSocket events
- Supports: binary sensors, sensors, switches, buttons, selects, images, cameras
- Commands sent back to Scrypted via REST

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
