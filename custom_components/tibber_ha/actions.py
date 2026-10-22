"""Explicit write actions with read-back, not charging automation."""
from datetime import time

import voluptuous as vol
from homeassistant.core import SupportsResponse
from homeassistant.exceptions import HomeAssistantError
from tibberlib import TibberClient, TibberError
from tibberlib.discovery import read_vehicle

from .const import DOMAIN
from .validation import departure_readback_matches

DAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")


def _soc(value):
    if type(value) is not int or not 0 <= value <= 100:
        raise vol.Invalid("SoC must be an integer from 0 to 100")
    return value


def _selected(hass, vehicle_id):
    candidates = list(hass.data.get(DOMAIN, {}).values())
    matches = [c for c in candidates if not vehicle_id or c.entry.data["vehicle_id"] == vehicle_id]
    if len(matches) != 1:
        raise HomeAssistantError("Select exactly one configured vehicle")
    return matches[0]


def async_register_actions(hass):
    async def perform(call):
        coordinator = _selected(hass, call.data.get("vehicle_id"))
        async with coordinator.write_lock:
            await coordinator.async_refresh()
            if not coordinator.last_update_success:
                raise HomeAssistantError("Unable to read current vehicle before writing")
            home_id = coordinator.entry.data.get("home_id")
            if not home_id:
                raise HomeAssistantError("Home selection required; configure the integration again")
            vehicle_id = coordinator.entry.data["vehicle_id"]

            async def token():
                return coordinator.token

            client = TibberClient(coordinator.http, token)
            departures = None
            if call.service == "set_departure_time":
                departure = time.fromisoformat(call.data["time"])
                if departure.tzinfo is not None or departure.second or departure.microsecond:
                    raise HomeAssistantError("Use local HH:MM time, without seconds or timezone")
                departures = {call.data["weekday"]: departure}
                if call.data.get("clear_other_days"):
                    departures = {day: departures.get(day) for day in DAYS}
            elif call.service == "clear_departure_times":
                departures = {day: None for day in call.data["weekdays"]}
            try:
                if departures is not None:
                    await client.set_departure_times(
                        vehicle_id=vehicle_id, home_id=home_id, departures=departures,
                    )
                else:
                    await client.set_vehicle_soc(
                        vehicle_id=vehicle_id, home_id=home_id,
                        battery_level=call.data["battery_level"],
                    )
                snapshot = await read_vehicle(coordinator.token, vehicle_id)
            except TibberError as err:
                raise HomeAssistantError(str(err)) from err
            coordinator.async_set_updated_data(snapshot)
            if departures is not None:
                if not departure_readback_matches(snapshot, departures):
                    raise HomeAssistantError("Write sent but departure read-back did not match; do not blindly retry")
            elif (snapshot.get("battery") or {}).get("level") != call.data["battery_level"]:
                raise HomeAssistantError("Write sent but SoC read-back did not match; do not blindly retry")
            return {"verified": True}

    base = {vol.Optional("vehicle_id"): str}
    schemas = {
        "set_vehicle_soc": vol.Schema({**base,
            vol.Required("battery_level"): _soc}),
        "set_departure_time": vol.Schema({**base,
            vol.Required("weekday"): vol.In(DAYS),
            vol.Optional("clear_other_days", default=False): bool,
            vol.Required("time"): vol.Match(r"^(?:[01]\d|2[0-3]):[0-5]\d$")}),
        "clear_departure_times": vol.Schema({**base,
            vol.Required("weekdays"): vol.All([vol.In(DAYS)], vol.Length(min=1, max=7))}),
    }
    for name, schema in schemas.items():
        if not hass.services.has_service(DOMAIN, name):
            hass.services.async_register(DOMAIN, name, perform, schema=schema,
                                         supports_response=SupportsResponse.OPTIONAL)
