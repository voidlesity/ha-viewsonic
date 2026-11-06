"""Shared state for ViewSonic commercial displays (CDE/LFD series).

A single coordinator owns the one TCP connection to the display and polls it;
all entities (media player, numbers, switches, ...) read from and send commands
through it. The display does not cope well with several parallel connections.
"""

from __future__ import annotations

import logging
import time
from datetime import timedelta

from homeassistant.exceptions import HomeAssistantError  # type: ignore
from homeassistant.helpers import device_registry as dr  # type: ignore
from homeassistant.helpers.entity import DeviceInfo  # type: ignore
from homeassistant.helpers.update_coordinator import (  # type: ignore
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import (
    CONF_HOST,
    CONF_MAC,
    CONF_NAME,
    DISPLAY_MODELS,
    DISPLAY_POWER_GRACE,
    DOMAIN,
    INTERVALS,
    LFD_PORT,
    host_unique_id,
)
from .lfd import LFDClient, LFDError, send_wake_on_lan, wake_on_lan_targets

_LOGGER = logging.getLogger(__name__)

# Settings that can be read back from the display: key -> (command, command type)
POLLED_SETTINGS = {
    "brightness": ("b", "g"),
    "contrast": ("a", "g"),
    "color": ("d", "g"),
    "tint": ("e", "g"),
    "backlight_level": ("B", "a"),
    "backlight": ("h", "g"),
    "freeze": ("i", "g"),
    "remote_control": ("n", "g"),
    "power_lock": ("o", "g"),
    "button_lock": ("p", "g"),
    "menu_lock": ("q", "g"),
    "temperature": ("0", "g"),
    "operating_hours": ("1", "g"),
}

# Settings are polled less often than power/volume/mute/input
SETTINGS_POLL_EVERY = 6


class ViewSonicDisplayCoordinator(DataUpdateCoordinator[dict]):
    def __init__(self, hass, entry):
        self.entry = entry
        self.host = entry.data[CONF_HOST]
        self.device_name = entry.data.get(CONF_NAME, "ViewSonic Display")
        self.model = entry.data.get("model", "display-unknown")
        self.mac = entry.data.get(CONF_MAC)
        self.unique_id = host_unique_id(self.host)
        self.reduce_traffic = entry.data.get("reduce traffic", False)
        self.client = LFDClient(self.host, LFD_PORT, timeout=INTERVALS["timeout"])

        self.input_labels: dict[str, str] = {}
        self.input_codes: list[str] = list(DISPLAY_MODELS[self.model])
        self.sw_version = None
        self.serial = None
        self._info_loaded = False
        self._cycle = 0
        self._power_override = None
        self._power_override_until = 0.0

        interval = (
            INTERVALS["slow_update"] if self.reduce_traffic else INTERVALS["update"]
        )
        super().__init__(
            hass,
            _LOGGER,
            name=f"ViewSonic display {self.host}",
            update_interval=timedelta(seconds=interval),
            config_entry=entry,
        )

    @property
    def device_info(self) -> DeviceInfo:
        info = DeviceInfo(
            identifiers={(DOMAIN, self.unique_id)},
            name=self.device_name,
            manufacturer="ViewSonic",
            model=self.model,
            connections={(DOMAIN, self.host)},
        )
        if self.mac:
            info["connections"].add((dr.CONNECTION_NETWORK_MAC, self.mac))
        if self.sw_version:
            info["sw_version"] = self.sw_version
        if self.serial:
            info["serial_number"] = self.serial
        return info

    @property
    def is_on(self) -> bool:
        """The display is on and can be controlled."""
        return bool(self.data and self.data["reachable"] and self.data["on"])

    def _grace(self) -> bool | None:
        if (
            self._power_override is not None
            and time.time() < self._power_override_until
        ):
            return self._power_override
        self._power_override = None
        return None

    async def _async_update_data(self) -> dict:
        data = dict(
            self.data
            or {
                "reachable": False,
                "on": False,
                "power": False,
                "volume": None,
                "mute": None,
                "input": None,
                "signal": None,
            }
        )
        data["settings"] = dict((self.data or {}).get("settings", {}))
        was_on = data["on"]
        was_reachable = data["reachable"]

        try:
            if not self._info_loaded:
                await self._async_load_info()
            power = await self.client.get("l")
            data["reachable"] = True
            data["on"] = power == "001"
            if data["on"]:
                await self._async_poll_on(data, poll_settings=not was_on)
            if not was_reachable:
                _LOGGER.debug("Display %s is reachable, power=%s", self.host, power)
        except LFDError as err:
            # The display closes its control port in standby, so this is expected when off
            if was_reachable:
                _LOGGER.debug(
                    "Display %s is not responding (standby?): %s", self.host, err
                )
            data["reachable"] = False
            data["on"] = False

        grace = self._grace()
        if grace is not None and grace == data["on"]:
            self._power_override = None
            grace = None
        data["power"] = grace if grace is not None else data["on"]
        return data

    async def _async_poll_on(self, data, poll_settings):
        volume = await self.client.get("f")
        data["volume"] = int(volume) if volume and volume.isdigit() else None

        mute = await self.client.get("g")
        data["mute"] = mute == "001" if mute in ("000", "001") else None

        source = await self.client.get("j")
        if source and len(source) == 3:
            # 1st digit is signal detection, the remaining two digits are the input code
            data["signal"] = source[0] == "1"
            data["input"] = "0" + source[1:].upper()

        self._cycle += 1
        if (
            poll_settings
            or self.reduce_traffic
            or self._cycle % SETTINGS_POLL_EVERY == 0
        ):
            for key, (command, cmd_type) in POLLED_SETTINGS.items():
                data["settings"][key] = await self.client.get(
                    command, cmd_type=cmd_type
                )

    async def _async_load_info(self):
        inputs = await self.client.get_inputs()
        if inputs:
            self.input_labels = inputs
            self.input_codes = list(inputs)

        mac = await self.client.get("5")
        if mac and len(mac) == 12:
            mac = ":".join(mac[i : i + 2] for i in range(0, 12, 2)).lower()
            if mac != self.mac:
                self.mac = mac
                # Persist the MAC so Wake-on-LAN works after a restart while the display is off
                self.hass.config_entries.async_update_entry(
                    self.entry, data={**self.entry.data, CONF_MAC: mac}
                )

        self.sw_version = await self.client.get("8")
        self.serial = await self.client.get("7")
        self._info_loaded = True

        device = dr.async_get(self.hass).async_get_device(
            identifiers={(DOMAIN, self.unique_id)}
        )
        if device:
            dr.async_get(self.hass).async_update_device(
                device.id, sw_version=self.sw_version, serial_number=self.serial
            )

    async def async_send(self, command: str, value: str, cmd_type: str = "s"):
        """Send a set command, raising a HomeAssistantError if it fails."""
        try:
            ok = await self.client.set(command, value, cmd_type)
        except LFDError as err:
            raise HomeAssistantError(
                f"Unable to send command to display {self.host}: {err}"
            ) from err
        if not ok:
            raise HomeAssistantError(
                f"Display {self.host} rejected command {cmd_type}{command}{value}"
            )

    async def async_set_setting(
        self, key: str, command: str, value: str, cmd_type: str = "s"
    ):
        """Send a set command and store the new value for a polled setting."""
        await self.async_send(command, value, cmd_type)
        self.data["settings"][key] = value
        self.async_update_listeners()

    def update_data(self, **changes):
        self.data.update(changes)
        self.async_update_listeners()

    async def async_turn_on(self):
        if self.mac:
            try:
                await self.hass.async_add_executor_job(
                    send_wake_on_lan, self.mac, wake_on_lan_targets(self.host)
                )
            except (OSError, ValueError) as err:
                _LOGGER.warning("Failed to send Wake-on-LAN to %s: %s", self.mac, err)
        elif not self.client.connected:
            _LOGGER.warning(
                "MAC address of display %s is unknown, so it can't be woken from standby. "
                "It is learned automatically the next time the display is on.",
                self.host,
            )
        try:
            await self.client.set("!", "001")
        except LFDError as err:
            # In standby the control port is closed; Wake-on-LAN does the job there
            if not self.mac:
                raise HomeAssistantError(
                    f"Unable to turn on display {self.host}: {err}"
                ) from err
        self._set_power_override(True)

    async def async_turn_off(self):
        await self.async_send("!", "000")
        self._set_power_override(False)

    def _set_power_override(self, on: bool):
        self._power_override = on
        self._power_override_until = time.time() + DISPLAY_POWER_GRACE
        self.update_data(power=on)

    async def async_shutdown(self):
        await super().async_shutdown()
        await self.client.close()


class ViewSonicDisplayEntity(CoordinatorEntity[ViewSonicDisplayCoordinator]):
    """Base class for entities of a ViewSonic display."""

    _attr_has_entity_name = True
    # Only available while the display is on (it can't be controlled in standby)
    _requires_on = True

    def __init__(
        self,
        coordinator: ViewSonicDisplayCoordinator,
        key: str | None = None,
        name: str | None = None,
    ):
        super().__init__(coordinator)
        self._attr_unique_id = (
            coordinator.unique_id if key is None else f"{coordinator.unique_id}_{key}"
        )
        self._attr_name = name
        self._attr_device_info = coordinator.device_info

    @property
    def available(self) -> bool:
        if not super().available:
            return False
        return self.coordinator.is_on if self._requires_on else True

    @property
    def settings(self) -> dict:
        return self.coordinator.data["settings"]
