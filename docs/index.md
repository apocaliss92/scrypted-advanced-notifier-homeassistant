# Scrypted Advanced Notifier — Home Assistant integration

Custom integration for [Home Assistant](https://www.home-assistant.io/) that
connects to the [Scrypted Advanced Notifier](https://github.com/apocaliss92/scrypted-advanced-notifier)
plugin.

These pages are a **view** over this repository. Nothing is authored here that is
not also in the repo — `README.md` stays the file HACS renders, and the code stays
the source of truth for behaviour.

| Page | Start here if… |
| --- | --- |
| [installation.md](installation.md) | you are installing or configuring the integration |
| [architecture.md](architecture.md) | you want to know how the integration talks to Scrypted |
| [development.md](development.md) | you are changing the code, versions or the release pipeline |
| [hosting.md](hosting.md) | you want to read this on a phone, or deploy the site |

## What it does

- Automatic entity discovery from Scrypted cameras
- Real-time state updates via Home Assistant WebSocket events
- Supports: binary sensors, sensors, switches, buttons, selects, images, cameras
- Commands sent back to Scrypted via REST

## Not yet written

These are gaps, not omissions — the prose does not exist anywhere in the repo yet,
and inventing it here would be worse than leaving the list visible:

- [ ] Troubleshooting: what to check when entities never appear after setup
- [ ] The action listener (`action_listener.py`) and mobile-app notification
      actions, including snooze
- [ ] Per-platform notes: which Scrypted concept maps to which HA entity
- [ ] Upgrade notes between integration versions
