"""Diagnostic sensors for ViewSonic commercial displays."""

from homeassistant.components.sensor import (  # type: ignore
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfTemperature, UnitOfTime  # type: ignore
from homeassistant.helpers.entity import EntityCategory  # type: ignore

from .const import DOMAIN
from .display import ViewSonicDisplayEntity


async def async_setup_entry(hass, config_entry, async_add_entities):
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    async_add_entities(
        [
            DisplayTemperatureSensor(coordinator, "temperature", "Temperature"),
            DisplayOperatingHoursSensor(
                coordinator, "operating_hours", "Operating hours"
            ),
        ]
    )


def _to_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


class DisplayTemperatureSensor(ViewSonicDisplayEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self):
        # 000~100 for 0~100 °C, -01~-99 for negative values
        return _to_int(self.settings.get("temperature"))


class DisplayOperatingHoursSensor(ViewSonicDisplayEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = UnitOfTime.HOURS
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:timer-outline"

    @property
    def native_value(self):
        return _to_int(self.settings.get("operating_hours"))
