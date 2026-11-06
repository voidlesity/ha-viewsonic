"""Number entities (picture and audio levels) for ViewSonic commercial displays."""

from homeassistant.components.number import NumberMode, RestoreNumber  # type: ignore
from homeassistant.helpers.entity import EntityCategory  # type: ignore

from .const import DOMAIN
from .display import ViewSonicDisplayEntity

# key, name, set command, set command type, icon, can be read back from the display
NUMBERS = [
    ("brightness", "Picture brightness", "$", "s", "mdi:brightness-6", True),
    ("contrast", "Picture contrast", "#", "s", "mdi:contrast-box", True),
    ("color", "Picture color", "&", "s", "mdi:palette", True),
    ("tint", "Picture tint", "'", "s", "mdi:format-color-fill", True),
    (
        "backlight_level",
        "Picture backlight",
        "B",
        "A",
        "mdi:television-ambient-light",
        True,
    ),
    ("bass", "Audio bass", ".", "s", "mdi:speaker", False),
    ("treble", "Audio treble", "/", "s", "mdi:music-clef-treble", False),
    ("balance", "Audio balance", "0", "s", "mdi:scale-balance", False),
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
        # Shown until the display reports a value
        self._last_value = None

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        if last := await self.async_get_last_number_data():
            self._last_value = last.native_value

    @property
    def native_value(self):
        if self._readable:
            value = self.settings.get(self._key)
            if value and value.isdigit():
                return int(value)
        return self._last_value

    async def async_set_native_value(self, value: float):
        value = f"{int(value):03d}"
        if self._readable:
            await self.coordinator.async_set_setting(
                self._key, self._command, value, self._cmd_type
            )
        else:
            await self.coordinator.async_send(self._command, value, self._cmd_type)
            self._last_value = int(value)
            self.async_write_ha_state()
