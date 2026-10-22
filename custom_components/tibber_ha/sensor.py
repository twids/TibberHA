"""Expose account settings for inspection, without duplicating Renault SoC."""
from homeassistant.components.sensor import SensorEntity
from homeassistant.const import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity


async def async_setup_entry(hass, entry, async_add_entities):
    from .const import DOMAIN
    async_add_entities([SettingsSensor(hass.data[DOMAIN][entry.entry_id])])


class SettingsSensor(CoordinatorEntity, SensorEntity):
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:car-cog"

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.data['vehicle_id']}_settings"
        self._attr_name = f"TibberHA {coordinator.entry.title} settings"

    @property
    def native_value(self):
        return "read_only"

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data or {}
        # Only disclose setting key metadata here. Raw values/actions may
        # contain account information and belong in a targeted local inspection.
        return {
            "setting_keys": [s.get("key") for s in data.get("userSettings", [])],
            "departure_times": (data.get("charging") or {}).get("departureTimes"),
            "write_enabled": False,
        }
