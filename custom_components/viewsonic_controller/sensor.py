"""Diagnostic sensors for ViewSonic commercial displays."""

from homeassistant.components.sensor import (  # type: ignore
    RestoreSensor,
    SensorDeviceClass,
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


class DisplaySettingSensor(ViewSonicDisplayEntity, RestoreSensor):
    """A polled value; the last known value is kept while the display is off."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, key, name):
        super().__init__(coordinator, key, name)
        self._key = key
        self._restored_value = None

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        if last := await self.async_get_last_sensor_data():
            self._restored_value = last.native_value

    @property
    def native_value(self):
        value = _to_int(self.settings.get(self._key))
        return self._restored_value if value is None else value


class DisplayTemperatureSensor(DisplaySettingSensor):
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS


class DisplayOperatingHoursSensor(DisplaySettingSensor):
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = UnitOfTime.HOURS
    _attr_icon = "mdi:timer-outline"
