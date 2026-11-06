"""Switch entities for ViewSonic commercial displays."""

from homeassistant.components.switch import SwitchEntity  # type: ignore
from homeassistant.helpers.entity import EntityCategory  # type: ignore

from .const import DOMAIN
from .display import ViewSonicDisplayEntity

# key, name, set command, icon, entity category
SWITCHES = [
    ("backlight", "Backlight", "(", "mdi:lightbulb-on-outline", None),
    ("freeze", "Freeze picture", "*", "mdi:snowflake", None),
    ("power_lock", "Power lock", "4", "mdi:power-plug-off", EntityCategory.CONFIG),
    (
        "button_lock",
        "Button lock",
        "8",
        "mdi:gesture-tap-button",
        EntityCategory.CONFIG,
    ),
    ("menu_lock", "Menu lock", ">", "mdi:menu", EntityCategory.CONFIG),
]


async def async_setup_entry(hass, config_entry, async_add_entities):
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    async_add_entities(DisplaySwitch(coordinator, *switch) for switch in SWITCHES)


class DisplaySwitch(ViewSonicDisplayEntity, SwitchEntity):
    def __init__(self, coordinator, key, name, command, icon, category):
        super().__init__(coordinator, key, name)
        self._key = key
        self._command = command
        self._attr_icon = icon
        self._attr_entity_category = category

    @property
    def is_on(self):
        value = self.settings.get(self._key)
        return None if value is None else value == "001"

    async def async_turn_on(self, **kwargs):
        await self.coordinator.async_set_setting(self._key, self._command, "001")

    async def async_turn_off(self, **kwargs):
        await self.coordinator.async_set_setting(self._key, self._command, "000")
