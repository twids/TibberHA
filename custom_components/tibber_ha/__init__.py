"""Tibber app account and explicit HA actions. No autonomous charging policy."""
import asyncio
import time
from datetime import timedelta

import httpx
import voluptuous as vol
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import SupportsResponse
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from tibberlib import TibberClient, TibberError
from tibberlib.discovery import list_homes, login, read_vehicle

from .const import DOMAIN
from .recovery import read_with_reauthentication


class TibberCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, entry):
        import logging
        super().__init__(hass, logging.getLogger(__name__), name=DOMAIN,
                         update_interval=timedelta(minutes=15))
        self.entry = entry
        self.http = httpx.AsyncClient()
        self.token = None
        self.token_until = 0
        self.write_lock = asyncio.Lock()

    async def _authenticate(self):
        self.token = await login(self.http, self.entry.data[CONF_USERNAME],
                                 self.entry.data[CONF_PASSWORD])
        # Conservative renewal before the observed ~3-hour failures. The server's
        # actual token lifetime is undocumented; read recovery also handles early expiry.
        self.token_until = time.monotonic() + 2 * 3600

    async def _read_snapshot(self):
        if not self.token or time.monotonic() >= self.token_until:
            await self._authenticate()
        if "home_id" not in self.entry.data:
            homes = await list_homes(self.http, self.token)
            if len(homes) == 1:
                self.hass.config_entries.async_update_entry(
                    self.entry, data={**self.entry.data, "home_id": homes[0]["id"]}
                )
        return await read_vehicle(self.token, self.entry.data["vehicle_id"])

    async def _async_update_data(self):
        try:
            return await read_with_reauthentication(self._read_snapshot, self._authenticate)
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
            vehicle_id = call.data.get("vehicle_id")
            candidates = list(hass.data[DOMAIN].values())
            selected = (next((c for c in candidates
                             if c.entry.data["vehicle_id"] == vehicle_id), None)
                        if vehicle_id else candidates[0] if len(candidates) == 1 else None)
            if selected is None:
                raise HomeAssistantError("Vehicle is not configured in TibberHA")
            await selected.async_request_refresh()
            if not selected.last_update_success:
                raise HomeAssistantError("Unable to read vehicle settings")
            data = selected.data
            # Explicit, local inspection only. No tokens, credentials or action URLs.
            return {"vehicle_id": selected.entry.data["vehicle_id"],
                    "settings": data.get("userSettings", []),
                    "layout": data.get("settingsScreen", []),
                    "charging": data.get("charging"),
                    "actions": [{k: a.get(k) for k in ("text", "type", "action", "enabled")}
                                for a in data.get("actionButtons", [])]}
        hass.services.async_register(
            DOMAIN, "inspect_settings", inspect_settings,
            schema=vol.Schema({vol.Optional("vehicle_id"): str}),
            supports_response=SupportsResponse.ONLY,
        )
    await hass.config_entries.async_forward_entry_setups(entry, [Platform.SENSOR])
    from .actions import async_register_actions
    async_register_actions(hass)
    return True


async def async_unload_entry(hass, entry):
    unloaded = await hass.config_entries.async_unload_platforms(entry, [Platform.SENSOR])
    if unloaded:
        coordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.http.aclose()
        if not hass.data[DOMAIN]:
            hass.services.async_remove(DOMAIN, "inspect_settings")
            for name in ("set_vehicle_soc", "set_departure_time", "clear_departure_times"):
                hass.services.async_remove(DOMAIN, name)
    return unloaded
