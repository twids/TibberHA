"""Read-only discovery stage; no charge control or SoC writes enabled."""
import time
from datetime import timedelta

import httpx
import voluptuous as vol
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import SupportsResponse
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from tibberlib import TibberError
from tibberlib.discovery import login, read_vehicle

from .const import DOMAIN


class TibberCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, entry):
        import logging
        super().__init__(hass, logging.getLogger(__name__), name=DOMAIN,
                         update_interval=timedelta(minutes=15))
        self.entry = entry
        self.http = httpx.AsyncClient()
        self.token = None
        self.token_until = 0

    async def _async_update_data(self):
        try:
            if not self.token or time.monotonic() >= self.token_until:
                self.token = await login(self.http, self.entry.data[CONF_USERNAME],
                                         self.entry.data[CONF_PASSWORD])
                self.token_until = time.monotonic() + 17 * 3600
            return await read_vehicle(self.token, self.entry.data["vehicle_id"])
        except TibberError as err:
            self.token = None
            raise UpdateFailed(str(err)) from err


async def async_setup_entry(hass, entry):
    coordinator = TibberCoordinator(hass, entry)
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception:
        await coordinator.http.aclose()
        raise
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    if not hass.services.has_service(DOMAIN, "inspect_settings"):
        async def inspect_settings(call):
            vehicle_id = call.data["vehicle_id"]
            selected = next((c for c in hass.data[DOMAIN].values()
                             if c.entry.data["vehicle_id"] == vehicle_id), None)
            if selected is None:
                raise HomeAssistantError("Vehicle is not configured in TibberHA")
            await selected.async_request_refresh()
            if not selected.last_update_success:
                raise HomeAssistantError("Unable to read vehicle settings")
            data = selected.data
            # Explicit, local inspection only. No tokens, credentials or action URLs.
            return {"settings": data.get("userSettings", []),
                    "layout": data.get("settingsScreen", []),
                    "charging": data.get("charging"),
                    "actions": [{k: a.get(k) for k in ("text", "type", "action", "enabled")}
                                for a in data.get("actionButtons", [])]}
        hass.services.async_register(
            DOMAIN, "inspect_settings", inspect_settings,
            schema=vol.Schema({vol.Required("vehicle_id"): str}),
            supports_response=SupportsResponse.ONLY,
        )
    await hass.config_entries.async_forward_entry_setups(entry, [Platform.SENSOR])
    return True


async def async_unload_entry(hass, entry):
    unloaded = await hass.config_entries.async_unload_platforms(entry, [Platform.SENSOR])
    if unloaded:
        coordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.http.aclose()
        if not hass.data[DOMAIN]:
            hass.services.async_remove(DOMAIN, "inspect_settings")
    return unloaded
