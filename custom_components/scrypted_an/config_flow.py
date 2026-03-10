"""Config flow for Scrypted Advanced Notifier."""
from __future__ import annotations

import logging

import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    CONF_HA_SECRET,
    CONF_SCRYPTED_URL,
    CONF_SELECTED_DEVICE_IDS,
    DOMAIN,
    ENDPOINT_HA_DEVICES,
)

_LOGGER = logging.getLogger(__name__)


async def _fetch_devices(
    scrypted_url: str, ha_secret: str, origin: str
) -> tuple[list[dict], str | None]:
    """Fetch available devices from the plugin and return (devices, error_key)."""
    url = f"{scrypted_url}{ENDPOINT_HA_DEVICES}"
    headers = {
        "Authorization": f"Bearer {ha_secret}",
        "Origin": origin,
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url, headers=headers, timeout=aiohttp.ClientTimeout(total=10), ssl=False
            ) as resp:
                if resp.status == 401:
                    return [], "invalid_secret"
                if resp.status == 403:
                    _LOGGER.error(
                        "Origin not allowed by Scrypted plugin. Sent Origin: '%s'. "
                        "Add this URL to the plugin's haAllowedOrigins setting.",
                        origin,
                    )
                    return [], "origin_not_allowed"
                if resp.status != 200:
                    return [], "cannot_connect"
                data = await resp.json()
                return data.get("devices", []), None
    except aiohttp.ClientConnectorError:
        return [], "cannot_connect"
    except Exception:
        return [], "cannot_connect"


def _build_select_schema(
    available_devices: list[dict], current_selection: list[str] | None = None
) -> vol.Schema:
    options = [
        SelectOptionDict(value=d["device_id"], label=d["device_name"])
        for d in available_devices
    ]
    default = current_selection or vol.UNDEFINED
    return vol.Schema(
        {
            vol.Required(CONF_SELECTED_DEVICE_IDS, default=default): SelectSelector(
                SelectSelectorConfig(
                    options=options,
                    multiple=True,
                    mode=SelectSelectorMode.LIST,
                )
            ),
        }
    )


class ScryptedAnConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Scrypted Advanced Notifier."""

    VERSION = 1

    def __init__(self) -> None:
        self._scrypted_url: str = ""
        self._ha_secret: str = ""
        self._available_devices: list[dict] = []

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> ScryptedAnOptionsFlow:
        """Return the options flow handler."""
        return ScryptedAnOptionsFlow()

    def _get_origin(self) -> str:
        return str(self.hass.config.external_url or self.hass.config.internal_url or "")

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        """Step 1: collect Scrypted URL + secret, validate connection."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._scrypted_url = user_input[CONF_SCRYPTED_URL].rstrip("/")
            self._ha_secret = user_input[CONF_HA_SECRET]

            devices, err = await _fetch_devices(
                self._scrypted_url, self._ha_secret, self._get_origin()
            )
            if err:
                errors["base"] = err
            else:
                self._available_devices = devices
                return await self.async_step_select_devices()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SCRYPTED_URL): str,
                    vol.Required(CONF_HA_SECRET): str,
                }
            ),
            errors=errors,
        )

    async def async_step_select_devices(
        self, user_input: dict | None = None
    ) -> FlowResult:
        """Step 2: multi-select which devices to import."""
        errors: dict[str, str] = {}

        if user_input is not None:
            selected = user_input.get(CONF_SELECTED_DEVICE_IDS, [])
            if not selected:
                errors[CONF_SELECTED_DEVICE_IDS] = "no_devices_selected"
            else:
                return self.async_create_entry(
                    title="Scrypted Advanced Notifier",
                    data={
                        CONF_SCRYPTED_URL: self._scrypted_url,
                        CONF_HA_SECRET: self._ha_secret,
                        CONF_SELECTED_DEVICE_IDS: selected,
                    },
                )

        return self.async_show_form(
            step_id="select_devices",
            data_schema=_build_select_schema(self._available_devices),
            errors=errors,
        )


class ScryptedAnOptionsFlow(config_entries.OptionsFlow):
    """Handle options for Scrypted Advanced Notifier (add/remove devices)."""

    def __init__(self) -> None:
        self._available_devices: list[dict] = []

    def _get_origin(self) -> str:
        return str(self.hass.config.external_url or self.hass.config.internal_url or "")

    async def async_step_init(self, user_input: dict | None = None) -> FlowResult:
        """Show device multi-select pre-populated with current selection."""
        errors: dict[str, str] = {}
        data = self.config_entry.data

        scrypted_url = data[CONF_SCRYPTED_URL]
        ha_secret = data[CONF_HA_SECRET]
        current_selection: list[str] = data.get(CONF_SELECTED_DEVICE_IDS, [])

        if not self._available_devices:
            devices, err = await _fetch_devices(scrypted_url, ha_secret, self._get_origin())
            if err:
                errors["base"] = err
                self._available_devices = [
                    {"device_id": did, "device_name": did} for did in current_selection
                ]
            else:
                self._available_devices = devices

        if user_input is not None:
            selected = user_input.get(CONF_SELECTED_DEVICE_IDS, [])
            if not selected:
                errors[CONF_SELECTED_DEVICE_IDS] = "no_devices_selected"
            else:
                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    data={**data, CONF_SELECTED_DEVICE_IDS: selected},
                )
                return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="init",
            data_schema=_build_select_schema(self._available_devices, current_selection),
            errors=errors,
        )
