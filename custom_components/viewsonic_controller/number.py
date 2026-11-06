"""Number entities (picture and audio levels) for ViewSonic commercial displays."""

from homeassistant.components.number import NumberMode, RestoreNumber  # type: ignore
from homeassistant.helpers.entity import EntityCategory  # type: ignore

from .const import DOMAIN
from .display import ViewSonicDisplayEntity

# key, name, set command, set command type, icon, can be read back from the display
NUMBERS = [
    ("brightness", "Brightness", "$", "s", "mdi:brightness-6", True),
    ("contrast", "Contrast", "#", "s", "mdi:contrast-box", True),
    ("color", "Color", "&", "s", "mdi:palette", True),
    ("tint", "Tint", "'", "s", "mdi:format-color-fill", True),
    ("backlight_level", "Backlight", "B", "A", "mdi:television-ambient-light", True),
    ("bass", "Bass", ".", "s", "mdi:speaker", False),
    ("treble", "Treble", "/", "s", "mdi:music-clef-treble", False),
    ("balance", "Balance", "0", "s", "mdi:scale-balance", False),
]


async def async_setup_entry(hass, config_entry, async_add_entities):
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    async_add_entities(DisplayNumber(coordinator, *number) for number in NUMBERS)


class DisplayNumber(ViewSonicDisplayEntity, RestoreNumber):
    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_step = 1
    _attr_mode = NumberMode.SLIDER
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator, key, name, command, cmd_type, icon, readable):
        super().__init__(coordinator, key, name)
        self._key = key
        self._command = command
        self._cmd_type = cmd_type
        self._readable = readable
        self._attr_icon = icon
        # The display can't report this value, so the last value set is shown
        self._attr_assumed_state = not readable
        self._assumed_value = None

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        if not self._readable and (last := await self.async_get_last_number_data()):
            self._assumed_value = last.native_value

    @property
    def native_value(self):
        if not self._readable:
            return self._assumed_value
        value = self.settings.get(self._key)
        return int(value) if value and value.isdigit() else None

    async def async_set_native_value(self, value: float):
        value = f"{int(value):03d}"
        if self._readable:
            await self.coordinator.async_set_setting(
                self._key, self._command, value, self._cmd_type
            )
        else:
            await self.coordinator.async_send(self._command, value, self._cmd_type)
            self._assumed_value = int(value)
            self.async_write_ha_state()
