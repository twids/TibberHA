"""Read-only account setup. Never changes a charging setting."""
import httpx
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from tibberlib import TibberError
from tibberlib.discovery import list_homes, list_vehicles, login, read_vehicle

from .const import DOMAIN


class TibberHAConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                async with httpx.AsyncClient() as http:
                    token = await login(http, user_input[CONF_USERNAME], user_input[CONF_PASSWORD])
                    vehicles = await list_vehicles(http, token)
                    homes = await list_homes(http, token)
                self._credentials = user_input
                self._token = token
                self._vehicles = {v["id"]: v.get("title") or v["id"] for v in vehicles}
                self._homes = {h["id"]: h.get("title") or h["id"] for h in homes}
                if not self._vehicles:
                    errors["base"] = "no_vehicles"
                else:
                    return await self.async_step_vehicle()
            except TibberError:
                errors["base"] = "cannot_connect"
        return self.async_show_form(
            step_id="user", errors=errors,
            data_schema=vol.Schema({vol.Required(CONF_USERNAME): str,
                                    vol.Required(CONF_PASSWORD): str}),
        )

    async def async_step_vehicle(self, user_input=None):
        errors = {}
        if user_input is not None:
            vehicle_id = user_input["vehicle_id"]
            try:
                await read_vehicle(self._token, vehicle_id)
            except TibberError:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(vehicle_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=self._vehicles[vehicle_id],
                    data={**self._credentials, "vehicle_id": vehicle_id,
                          "home_id": user_input["home_id"]},
                )
        return self.async_show_form(
            step_id="vehicle", errors=errors,
            data_schema=vol.Schema({vol.Required("vehicle_id"): vol.In(self._vehicles),
                                    vol.Required("home_id"): vol.In(self._homes)}),
        )
