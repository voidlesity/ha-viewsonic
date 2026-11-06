from homeassistant.components.binary_sensor import (  # type: ignore
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.helpers.entity import EntityCategory  # type: ignore

from .const import DOMAIN
from .display import ViewSonicDisplayEntity


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the binary sensor based on the media player state."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id].get("coordinator")
    if coordinator is not None:
        async_add_entities(
            [
                DisplayConnectionSensor(coordinator, "connection", "Connection"),
                DisplaySignalSensor(coordinator, "signal", "Signal detected"),
            ]
        )
        return

    projector = hass.data[DOMAIN][config_entry.entry_id]["projector"]
    connection = ProjectorConnectionSensor(projector)
    hass.data[DOMAIN][config_entry.entry_id]["connection"] = connection
    async_add_entities([connection], True)


class ProjectorConnectionSensor(BinarySensorEntity):
    """Binary sensor to indicate projector connection status."""

    def __init__(self, projector):
        """Initialize the sensor."""
        self._projector = projector
        self._attr_name = f"{projector.name} Connection"
        self._attr_device_class = "connectivity"  # Shows a network connection icon
        self._attr_unique_id = f"{projector.unique_id}_connection"
        self._attr_is_on = None

    @property
    def is_on(self):
        """Return True if the projector is connected."""
        return self._attr_is_on

    async def async_update(self):
        """Manually update the connection status from the projector."""
        self._attr_is_on = self._projector.is_connected


class DisplayConnectionSensor(ViewSonicDisplayEntity, BinarySensorEntity):
    """Whether the display's control port is reachable (it is closed in standby)."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def is_on(self):
        return self.coordinator.data["reachable"]


class DisplaySignalSensor(ViewSonicDisplayEntity, BinarySensorEntity):
    """Whether the current input has a video signal."""

    _attr_icon = "mdi:video-input-hdmi"

    @property
    def is_on(self):
        if not self.coordinator.is_on:
            return False
        return self.coordinator.data["signal"]
