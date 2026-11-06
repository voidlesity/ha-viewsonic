# Home Assistant Custom Integration - ViewSonic Controller

## Overview

A Home Assistant custom integration for controlling networked ViewSonic devices over the LAN:

- **Projectors** using the RS-232/LAN Control Protocol Specification V1.5 (TCP port 4661): power, source, volume and mute.
- **Commercial displays** (CDE/LFD series) using the LFD RS-232 & LAN Protocol (TCP port 5000): power, source, volume and mute plus picture, audio, lock and remote control settings.

This Project is heavily based on [nfeuerhelm/ha-proj-viewsonic](https://github.com/nfeuerhelm/ha-proj-viewsonic) that adds commercial display support.

## Supported devices

- ViewSonic projectors
  - One of: ls510w, ls510wh, ls560w, ls560wh, ls610hdh, ls610wh, ls832wu, pa504w, pa700s, pa700w, pa700x, ps502w, ps502x, px701-4ke, px704hd, px728-4k, px748-4k, px749-4k
  - Use 'unknown' for other ViewSonic projectors supporting the RS-232/LAN Control Protocol Specification V1.5
  - Projectors supporting older versions of the protocol may work using 'unknown', but your mileage may vary
  - **Pro9 series projectors are not supported**
- ViewSonic commercial displays
  - One of: cde75g3-1c
  - Use 'display-unknown' for other ViewSonic commercial displays supporting the LFD RS-232 & LAN Protocol

Home Assistant needs a working network connection to the device.

### Projectors

For full functionality, enable `Standby LAN Control` found in `ADVANCED` → `LAN Control Settings` or a similar menu location.

Entities:

- `media_player`: power, volume, mute and source
- `binary_sensor`: connection status

### Commercial displays

- Commercial displays close their LAN control port in standby. They are turned on via Wake-on-LAN, so Home Assistant must be on the same network segment as the display. The display's MAC address is read automatically the first time the integration connects while the display is on.
- Turning on takes around 10-20 seconds before the display can be controlled again.
- Volume is reported in the range 0-100 and volume up/down steps are supported.
- The labels configured for each input on the display are available in the `input_labels` attribute of the media player, and whether the current input has a signal in `signal_detected`.
- The display handles only one control connection reliably, so avoid running other LAN control software against it at the same time.

Entities (all except the media player and the connection sensor are unavailable while the display is off):

| Platform        | Entities                                                                  |
| --------------- | ------------------------------------------------------------------------- |
| `media_player`  | Power, volume (set/step), mute, source                                    |
| `number`        | Brightness, Contrast, Color, Tint, Backlight, Bass\*, Treble\*, Balance\* |
| `switch`        | Backlight, Freeze picture, Power lock, Button lock, Menu lock             |
| `select`        | Picture size\*, Color mode\*, Menu language\*, Remote control             |
| `sensor`        | Temperature, Operating hours                                              |
| `binary_sensor` | Connection, Signal detected                                               |
| `button`        | Remote keys (Up, Down, Left, Right, OK, Input, Menu, Exit), Sync clock    |

\* The display accepts these settings but cannot report them back. Home Assistant shows the last value it set (restored across restarts), so changes made with the remote or on-screen menu are not reflected.

Not supported by the display over LAN: sharpness (read-only, not exposed), surround sound, PIP, video wall/tiling.

## Installation

1. Download this repository.
2. Copy the `custom_components/viewsonic_controller` directory into `/config/custom_components/` on your Home Assistant instance.
3. Restart Home Assistant.

## Configuration

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=viewsonic_controller)

1. Go to `Settings` → `Devices & Services` → `Add Integration`.
2. Search for "ViewSonic Controller" and select it.
3. Enter the host, a name, the model and whether to reduce network traffic (poll every 30 instead of every 5 seconds).

Host, model and the traffic setting can be changed later via `Configure` on the integration entry. Changes are applied right away; when the host changes, existing entities and their history are kept.

## Contributing

Issues and pull requests are welcome via [Gitlab](https://git.voidlesity.dev/ha/viewsonic/issues).

## License

This project is licensed under the [MIT License](LICENSE).

## Credits

Originally developed by [@nfeuerhelm](https://github.com/nfeuerhelm) based on the [ViewSonic projector protocol](./docs/RS-232%20LAN%20Control%20Protocol%20Specification%20V1.5.pdf). Commercial display support is based on the [ViewSonic LFD RS-232 & LAN Protocol v3.3.1](./docs/LFD%20RS-232%20LAN%20Protocol%20V3.3.1.pdf).

## Trademark Legal Notices

All product names, trademarks and registered trademarks in this repository, are property of their respective owners. All product information in this repository is used by the project for identification purposes only.

The use of these names, trademarks and brands appearing in this repository, do not imply endorsement.
