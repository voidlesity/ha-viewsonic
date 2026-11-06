import logging

import voluptuous as vol  # type: ignore
from homeassistant import config_entries  # type: ignore
from homeassistant.core import callback  # type: ignore
from homeassistant.helpers.selector import (  # type: ignore
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
    selector,
)

from .const import CONF_HOST, CONF_NAME, DOMAIN, PROJECTOR_MODELS_LIST

_LOGGER = logging.getLogger(__name__)

CONF_MODEL = "model"
CONF_REDUCE_TRAFFIC = "reduce traffic"

TEXT = TextSelector(TextSelectorConfig(type=TextSelectorType.TEXT))
MODEL_SELECTOR = selector(
    {"select": {"options": PROJECTOR_MODELS_LIST, "mode": "dropdown"}}
)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): TEXT,
        vol.Required(CONF_NAME, default="ViewSonic"): TEXT,
        vol.Required(CONF_MODEL, default="unknown"): MODEL_SELECTOR,
        vol.Required(CONF_REDUCE_TRAFFIC, default=False): bool,
    }
)


def _host_in_use(hass, host, exclude_entry_id=None) -> bool:
    return any(
        entry.data.get(CONF_HOST) == host
        for entry in hass.config_entries.async_entries(DOMAIN)
        if entry.entry_id != exclude_entry_id
    )


class ViewSonicConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for ViewSonic projectors and displays."""

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        if user_input is not None:
            user_input[CONF_HOST] = user_input[CONF_HOST].strip()
            self._async_abort_entries_match({CONF_HOST: user_input[CONF_HOST]})
            return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)

        return self.async_show_form(step_id="user", data_schema=DATA_SCHEMA)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return ViewSonicOptionsFlow()


class ViewSonicOptionsFlow(config_entries.OptionsFlow):
    """Change host, model and polling of an existing entry."""

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        entry = self.config_entry
        errors = {}

        if user_input is not None:
            user_input[CONF_HOST] = user_input[CONF_HOST].strip()
            if _host_in_use(self.hass, user_input[CONF_HOST], entry.entry_id):
                errors[CONF_HOST] = "already_configured"
            else:
                # The integration reads its settings from the entry data, so apply
                # the changes there and reload to pick them up.
                self.hass.config_entries.async_update_entry(
                    entry, data={**entry.data, **user_input}
                )
                self.hass.config_entries.async_schedule_reload(entry.entry_id)
                return self.async_create_entry(data={})

        current = {**entry.data, **(user_input or {})}
        data_schema = vol.Schema(
            {
                vol.Required(CONF_HOST, default=current[CONF_HOST]): TEXT,
                vol.Required(
                    CONF_MODEL, default=current.get(CONF_MODEL, "unknown")
                ): MODEL_SELECTOR,
                vol.Required(
                    CONF_REDUCE_TRAFFIC,
                    default=current.get(CONF_REDUCE_TRAFFIC, False),
                ): bool,
            }
        )

        return self.async_show_form(
            step_id="init", data_schema=data_schema, errors=errors
        )
