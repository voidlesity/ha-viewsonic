"""ViewSonic projector and commercial display integration."""

import logging

from homeassistant.config_entries import ConfigEntry  # type: ignore
from homeassistant.core import HomeAssistant  # type: ignore
from homeassistant.helpers import device_registry as dr  # type: ignore
from homeassistant.helpers import entity_registry as er  # type: ignore

from .const import CONF_HOST, DISPLAY_MODELS, DOMAIN, host_unique_id

_LOGGER = logging.getLogger(__name__)

PROJECTOR_PLATFORMS = ["media_player", "binary_sensor"]
DISPLAY_PLATFORMS = [
    "media_player",
    "binary_sensor",
    "number",
    "switch",
    "select",
    "sensor",
    "button",
]


def _async_migrate_host(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Move the device and entities over to new unique IDs after a host change.

    Unique IDs are derived from the host, so without this every entity would be
    recreated (losing its history and customisations) when the host is changed.
    """
    new_id = host_unique_id(config_entry.data[CONF_HOST])
    dev_reg = dr.async_get(hass)
    ent_reg = er.async_get(hass)

    for device in dr.async_entries_for_config_entry(dev_reg, config_entry.entry_id):
        old_id = next(
            (value for domain, value in device.identifiers if domain == DOMAIN), None
        )
        if old_id is None or old_id == new_id:
            continue

        _LOGGER.info("Host changed, migrating unique IDs from %s to %s", old_id, new_id)
        for entity in er.async_entries_for_config_entry(ent_reg, config_entry.entry_id):
            if entity.unique_id == old_id or entity.unique_id.startswith(f"{old_id}_"):
                ent_reg.async_update_entity(
                    entity.entity_id,
                    new_unique_id=new_id + entity.unique_id[len(old_id) :],
                )
        dev_reg.async_update_device(
            device.id,
            new_identifiers={(DOMAIN, new_id)},
            new_connections={
                connection
                for connection in device.connections
                if connection[0] != DOMAIN
            }
            | {(DOMAIN, config_entry.data[CONF_HOST])},
        )


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up a ViewSonic device from a config entry."""
    _async_migrate_host(hass, config_entry)

    is_display = config_entry.data.get("model", "unknown") in DISPLAY_MODELS
    platforms = DISPLAY_PLATFORMS if is_display else PROJECTOR_PLATFORMS

    hass.data.setdefault(DOMAIN, {})
    entry_data = hass.data[DOMAIN][config_entry.entry_id] = {
        "projector": None,
        "connection": None,
        "coordinator": None,
        # Remembered so unloading still works after the model was changed
        "platforms": platforms,
    }

    if is_display:
        from .display import ViewSonicDisplayCoordinator

        coordinator = ViewSonicDisplayCoordinator(hass, config_entry)
        await coordinator.async_config_entry_first_refresh()
        entry_data["coordinator"] = coordinator

    await hass.config_entries.async_forward_entry_setups(config_entry, platforms)

    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    entry_data = hass.data[DOMAIN][config_entry.entry_id]

    unload_ok = await hass.config_entries.async_unload_platforms(
        config_entry, entry_data["platforms"]
    )

    if unload_ok:
        hass.data[DOMAIN].pop(config_entry.entry_id)
        if entry_data["coordinator"] is not None:
            await entry_data["coordinator"].async_shutdown()

    return unload_ok
