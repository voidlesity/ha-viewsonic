"""Switch entities for ViewSonic commercial displays."""

from homeassistant.components.switch import SwitchEntity  # type: ignore
from homeassistant.const import STATE_OFF, STATE_ON  # type: ignore
from homeassistant.helpers.entity import EntityCategory  # type: ignore
from homeassistant.helpers.restore_state import RestoreEntity  # type: ignore

from .const import DOMAIN
from .display import ViewSonicDisplayEntity

# key, name, set command, icon, entity category
SWITCHES = [
    ("backlight", "Backlight", "(", "mdi:lightbulb-on-outline", None),
    ("freeze", "Freeze picture", "*", "mdi:snowflake", None),
    ("power_lock", "Lock power", "4", "mdi:power-plug-off", EntityCategory.CONFIG),
    (
        "button_lock",
        "Lock buttons",
        "8",
        "mdi:gesture-tap-button",
        EntityCategory.CONFIG,
    ),
    ("menu_lock", "Lock menu", ">", "mdi:menu", EntityCategory.CONFIG),
]


async def async_setup_entry(hass, config_entry, async_add_entities):
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    async_add_entities(DisplaySwitch(coordinator, *switch) for switch in SWITCHES)


class DisplaySwitch(ViewSonicDisplayEntity, SwitchEntity, RestoreEntity):
    def __init__(self, coordinator, key, name, command, icon, category):
        super().__init__(coordinator, key, name)
        self._key = key
        self._command = command
        self._attr_icon = icon
        self._attr_entity_category = category
        # Shown until the display reports a value
        self._restored_is_on = None

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last and last.state in (STATE_ON, STATE_OFF):
            self._restored_is_on = last.state == STATE_ON

    @property
    def is_on(self):
        value = self.settings.get(self._key)
        if value is None:
            return self._restored_is_on
        return value == "001"

    async def async_turn_on(self, **kwargs):
        await self.coordinator.async_set_setting(self._key, self._command, "001")

    async def async_turn_off(self, **kwargs):
        await self.coordinator.async_set_setting(self._key, self._command, "000")
