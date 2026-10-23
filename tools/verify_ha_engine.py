"""Run in the official HA container. No Tibber network requests are made.

docker run --rm --network none -v C:/dev/TibberHA:/project:ro \
  --entrypoint python ghcr.io/home-assistant/home-assistant:2026.10.2 \
  /project/tools/verify_ha_engine.py
"""
import asyncio
from pathlib import Path
import tempfile

import yaml
from homeassistant.core import HomeAssistant, SupportsResponse
from homeassistant.exceptions import HomeAssistantError
from homeassistant.setup import async_setup_component
from homeassistant import loader

ROOT = Path(__file__).resolve().parents[1]
INPUTS = {"soc": "sensor.test_soc", "plugged": "binary_sensor.test_plug",
          "location": "device_tracker.test_car", "settings": "sensor.test_settings",
          "session": "input_text.test_session"}


class Loader(yaml.SafeLoader):
    pass


Loader.add_constructor("!input", lambda loader, node: INPUTS[loader.construct_scalar(node)])


async def main():
    config = yaml.load((ROOT / "blueprints/automation/zoe_weekday_minimum.yaml").read_text(), Loader)
    config.pop("blueprint")
    config["alias"] = "Engine verification"
    config["id"] = "tibber_engine_verification"
    with tempfile.TemporaryDirectory() as directory:
        hass = HomeAssistant(directory)
        loader.async_setup(hass)
        calls = []
        fail_schedule = False

        async def fake(call):
            calls.append((call.service, dict(call.data)))
            if fail_schedule and call.service == "set_departure_time":
                raise HomeAssistantError("Simulated verification failure")
            return {"verified": True}

        for name in ("set_vehicle_soc", "set_departure_time", "clear_departure_times"):
            hass.services.async_register("tibber_ha", name, fake,
                                         supports_response=SupportsResponse.OPTIONAL)
        try:
            assert await async_setup_component(hass, "homeassistant", {
                "homeassistant": {"time_zone": "Europe/Stockholm"}})
            assert await async_setup_component(hass, "input_text", {
                "input_text": {"test_session": {"max": 255}}})
            assert await async_setup_component(hass, "persistent_notification", {})
            hass.states.async_set(INPUTS["soc"], "20")
            hass.states.async_set(INPUTS["plugged"], "off")
            hass.states.async_set(INPUTS["location"], "home")
            hass.states.async_set(INPUTS["settings"], "connected", {"vehicle_id": "test-zoe"})
            assert await async_setup_component(hass, "automation", {"automation": [config]})
            await hass.async_start()
            await hass.async_block_till_done()
            assert not calls, calls

            hass.states.async_set(INPUTS["plugged"], "on")
            await hass.async_block_till_done()
            assert [name for name, _ in calls] == ["set_departure_time", "set_vehicle_soc"], calls
            assert calls[-1][1]["battery_level"] == 80, calls
            assert calls[0][1]["clear_other_days"] is True, calls
            assert '"waiting"' in hass.states.get(INPUTS["session"]).state
            print("PASS: plug-in below 40 writes one schedule and one adjusted SoC")

            hass.states.async_set(INPUTS["soc"], "25")
            await hass.async_block_till_done()
            assert len(calls) == 2, calls
            print("PASS: charging below threshold does not rewrite SoC")

            hass.states.async_set(INPUTS["soc"], "40")
            await hass.async_block_till_done()
            assert [name for name, _ in calls[2:]] == ["clear_departure_times", "set_vehicle_soc"], calls
            assert calls[-1][1]["battery_level"] == 40
            hass.states.async_set(INPUTS["soc"], "41")
            await hass.async_block_till_done()
            assert len(calls) == 4, calls
            print("PASS: 40% clears schedule and reports real SoC exactly once")

            hass.states.async_set(INPUTS["plugged"], "off")
            await hass.async_block_till_done()
            hass.states.async_set(INPUTS["soc"], "60")
            hass.states.async_set(INPUTS["plugged"], "on")
            await hass.async_block_till_done()
            assert [name for name, _ in calls[4:]] == ["clear_departure_times", "set_vehicle_soc"], calls
            assert calls[-1][1]["battery_level"] == 60
            print("PASS: a new session above 40 uses real SoC and no departure")

            hass.states.async_set(INPUTS["plugged"], "unavailable")
            await hass.async_block_till_done()
            hass.states.async_set(INPUTS["plugged"], "on")
            await hass.async_block_till_done()
            assert len(calls) == 6, calls
            print("PASS: unavailable -> on is not treated as a new plug-in")

            hass.states.async_set(INPUTS["plugged"], "off")
            await hass.async_block_till_done()
            hass.states.async_set(INPUTS["soc"], "20")
            fail_schedule = True
            hass.states.async_set(INPUTS["plugged"], "on")
            await hass.async_block_till_done()
            assert len(calls) == 7 and calls[-1][0] == "set_departure_time", calls
            assert '"error"' in hass.states.get(INPUTS["session"]).state
            hass.states.async_set(INPUTS["soc"], "21")
            await hass.async_block_till_done()
            assert len(calls) == 7, calls
            print("PASS: failed schedule prevents SoC write and automatic retries")
        finally:
            await hass.async_stop()


if __name__ == "__main__":
    asyncio.run(main())
