"""Select entities for ViewSonic commercial displays."""

from homeassistant.components.select import SelectEntity  # type: ignore
from homeassistant.helpers.entity import EntityCategory  # type: ignore
from homeassistant.helpers.restore_state import RestoreEntity  # type: ignore

from .const import DOMAIN
from .display import ViewSonicDisplayEntity

# key, name, set command, {value: option}, icon, can be read back from the display
SELECTS = [
    (
        "picture_size",
        "Picture size",
        "1",
        {
            "000": "Full (16:9)",
            "001": "Normal (4:3)",
            "002": "Real (1:1)",
        },
        "mdi:aspect-ratio",
        False,
    ),
    (
        "color_mode",
        "Color mode",
        ")",
        {
            "000": "Normal",
            "001": "Warm",
            "002": "Cold",
            "003": "Personal",
        },
        "mdi:palette-swatch",
        False,
    ),
    (
        "remote_control",
        "Remote control",
        "B",
        {
            "000": "Disabled",
            "001": "Enabled",
            "002": "Pass through",
        },
        "mdi:remote-tv",
        True,
    ),
    (
        "osd_language",
        "Menu language",
        "2",
        {
            "000": "English",
            "001": "French",
            "002": "Spanish",
        },
        "mdi:translate",
        False,
    ),
]


async def async_setup_entry(hass, config_entry, async_add_entities):
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    async_add_entities(DisplaySelect(coordinator, *select) for select in SELECTS)


class DisplaySelect(ViewSonicDisplayEntity, SelectEntity, RestoreEntity):
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator, key, name, command, options, icon, readable):
        super().__init__(coordinator, key, name)
        self._key = key
        self._command = command
        self._values = options
        self._codes = {option: value for value, option in options.items()}
        self._readable = readable
        self._attr_options = list(options.values())
        self._attr_icon = icon
        # The display can't report this value, so the last value set is shown
        self._attr_assumed_state = not readable
        self._assumed_option = None

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        if not self._readable and (last := await self.async_get_last_state()):
            if last.state in self._codes:
                self._assumed_option = last.state

    @property
    def current_option(self):
        if not self._readable:
            return self._assumed_option
        return self._values.get(self.settings.get(self._key))

    async def async_select_option(self, option: str):
        value = self._codes[option]
        if self._readable:
            await self.coordinator.async_set_setting(self._key, self._command, value)
        else:
            await self.coordinator.async_send(self._command, value)
            self._assumed_option = option
            self.async_write_ha_state()
