"""Button entities (remote control keys, clock sync) for ViewSonic commercial displays."""

from homeassistant.components.button import ButtonEntity  # type: ignore
from homeassistant.helpers.entity import EntityCategory  # type: ignore
from homeassistant.util import dt as dt_util  # type: ignore

from .const import DOMAIN
from .display import ViewSonicDisplayEntity

# key, name, keypad value, icon
KEYS = [
    ("key_up", "up", "000", "mdi:arrow-up-bold"),
    ("key_down", "down", "001", "mdi:arrow-down-bold"),
    ("key_left", "left", "002", "mdi:arrow-left-bold"),
    ("key_right", "right", "003", "mdi:arrow-right-bold"),
    ("key_enter", "OK", "004", "mdi:checkbox-blank-circle"),
    ("key_input", "input", "005", "mdi:import"),
    ("key_menu", "menu", "006", "mdi:menu"),
    ("key_exit", "exit", "007", "mdi:exit-to-app"),
]


async def async_setup_entry(hass, config_entry, async_add_entities):
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    entities = [DisplayKeyButton(coordinator, *key) for key in KEYS]
    entities.append(
        DisplaySyncClockButton(coordinator, "sync_clock", "System clock sync")
    )
    async_add_entities(entities)


class DisplayKeyButton(ViewSonicDisplayEntity, ButtonEntity):
    """Simulates a key on the display's remote control / keypad."""

    def __init__(self, coordinator, key, name, value, icon):
        super().__init__(coordinator, key, f"Remote {name}")
        self._value = value
        self._attr_icon = icon

    async def async_press(self):
        await self.coordinator.async_send("A", self._value)


class DisplaySyncClockButton(ViewSonicDisplayEntity, ButtonEntity):
    """Sets the display's clock to Home Assistant's local time."""

    _attr_icon = "mdi:clock-check-outline"
    _attr_entity_category = EntityCategory.CONFIG

    async def async_press(self):
        now = dt_util.now()
        for command, value in (
            ("V", f"Y{now.year % 100:02d}"),
            ("V", f"M{now.month:02d}"),
            ("V", f"D{now.day:02d}"),
            ("W", f"H{now.hour:02d}"),
            ("W", f"M{now.minute:02d}"),
            ("W", f"S{now.second:02d}"),
        ):
            await self.coordinator.async_send(command, value)
