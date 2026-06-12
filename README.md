# PowerShades Home Assistant Integration

A Home Assistant custom integration for controlling PowerShades motorized blinds via UDP communication.

## Features

- **Cover Platform**: Control blinds as Home Assistant covers (open, close, set position)
- **Button Platform**: Additional buttons for specific blind operations
- **UDP Communication**: Direct UDP communication with PowerShades controllers
- **Config Flow**: Easy setup through Home Assistant's UI
- **Local Control**: No cloud dependencies, works entirely locally

## Prerequisites

It is unknown if UDP communication is enabled by default on every PowerShades controller. If the integration's discovery doesn't find your shade and manual entry with its IP address gives a "cannot connect" error, you may need to enable UDP on the device yourself. If you figure out how to enable UDP on a shade that didn't have it on by default, please open an issue and explain how, so it can be documented here.

### Finding your shade's IP address

The integration's discovery step will usually find shades on your network automatically. If you need to enter an IP manually:

- **Via the PowerShades App (Recommended)**: Open the official PowerShades mobile app, navigate to your desired shade, select Enable Configuration, and confirm the prompt. Scroll down to view the assigned IP address.
- **Via Your Router's DHCP Client List**: Log into your network router's administration panel and check the connected devices list. Look for a device manufactured by "Wideband Labs LLC" — this is likely your PowerShades device.

## Installation

### HACS Installation

This integration can be installed via HACS as a custom repository:

1. In HACS, go to **Settings** → **Repositories**
2. Click the **+** button to add a new repository
3. Enter the repository URL: `https://github.com/dstocking/powershades-homeassistant`
4. Select **Integration** as the category
5. Click **Add**
6. Once added, search for "PowerShades" in HACS
7. Click **Download**
8. Restart Home Assistant

**Note**: This integration uses semantic versioning with proper GitHub releases. The current version is `v0.1.0`.

### Manual Installation

1. Download this repository (clone or download ZIP)
2. Copy the `custom_components/powershades` folder to your Home Assistant `config/custom_components/` directory
3. Restart Home Assistant

## Configuration

1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for "PowerShades"
4. The integration scans your network and lists discovered shades — pick one, or choose manual entry and provide the shade's IP address
5. The device is verified before the entry is created; if it doesn't respond you'll get a "cannot connect" error

## Usage

### Cover Controls

Once configured, your PowerShades will appear as covers in Home Assistant. You can:

- **Open**: Fully open the blinds
- **Close**: Fully close the blinds  
- **Set Position**: Set blinds to a specific percentage (0-100)
- **Stop**: Stop blinds in their current position

### Button Controls

Each shade also gets buttons for:

- **Toggle Shade**: Open/close based on current position, or stop if moving
- **Identify**: Makes the shade motor wiggle so you can tell which physical shade this is (under Diagnostic)
- **Jog Up/Down, Set Upper/Lower Limit, Clear Limits, Step Up/Down**: Limit calibration tools (under the device's Configuration section). Typical workflow: jog near the desired position, step to fine-tune, then set the limit.

### Services

Besides the standard cover services, the integration provides `powershades.toggle_shade`, `powershades.jog_up`/`jog_down`, `powershades.step_up`/`step_down`, `powershades.set_upper_limit`/`set_lower_limit`/`clear_limits`, and `powershades.set_shade_name` (renames the shade on the device itself; the Home Assistant device name follows).

### Known Limitations

PowerShades devices send replies and asynchronous move feedback only to the **last controller that sent them a command** ("UDP master"). Avoid running PowerShades Config.NET or another driver at the same time as Home Assistant — control still works, but live position feedback may intermittently lag until the next poll.

### Diagnostic Sensors

Battery percentage and battery voltage are available as diagnostic sensor entities (disabled by default — enable them from the device page). Note: in versions before 0.2.0 these values were exposed as attributes on the cover entity; templates referencing `battery_percentage`/`battery_voltage_mv` cover attributes should switch to the sensors.

### Data Updates

The shade pushes its status to Home Assistant in real time whenever Home Assistant is the one controlling it ("UDP master"). On top of that, Home Assistant polls the shade every 10 seconds (every 5 seconds while the position is unknown) so that changes made by another controller — such as the PowerShades app or a Control4 system — are also picked up.

### Automation Examples

Open a shade in the morning:

```yaml
alias: Open bedroom shade
description: ""
triggers:
  - trigger: time
    at: "07:00:00"
conditions: []
actions:
  - action: cover.open_cover
    target:
      entity_id: cover.bedroom_shade
mode: single
```

Close shades at dusk:

```yaml
alias: Close shades at dusk
description: ""
triggers:
  - trigger: state
    entity_id:
      - sensor.sun_next_dusk
conditions:
  - condition: state
    entity_id: cover.bedroom_shade
    state: "open"
actions:
  - action: cover.close_cover
    target:
      entity_id:
        - cover.bedroom_shade
mode: single
```

## Requirements

- Home Assistant 2023.8.0 or newer
- PowerShades controller with UDP communication enabled

## Supported Devices

This integration supports PowerShades controllers that communicate via UDP protocol.

## Troubleshooting

### HACS Installation Issues

If you encounter errors when installing via HACS:

1. **Version Error**: Ensure the repository has a proper release tag (currently `v0.1.0`)
2. **Repository Not Found**: Verify the repository URL is correct and the repository is public
3. **Download Failed**: Try refreshing HACS and clearing the cache

### Debug Logging

Enable debug logging by adding to your `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.powershades: debug
```

## Removing This Integration

Removing this integration is the same as most HACS integrations:

- Go to **Settings** → **Devices & Services** and select the PowerShades integration card.
- From the list of devices, select the PowerShades entry.
- Next to the entry, select the three-dot menu, then select **Delete**.
- If installed through HACS, go to HACS, select the three-dot menu for this integration, then select **Remove**.
- If you did a manual installation, delete the `custom_components/powershades` folder, then restart Home Assistant to clear the cache.

## Development

### Contributing

1. Fork this repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- PowerShades for their UDP protocol documentation
- Home Assistant community for the integration framework

## Support

For issues and feature requests, please use the [GitHub Issues](https://github.com/yourusername/powershades-homeassistant/issues) page.

## Changelog

### 0.2.0
- Rewrote UDP communication on asyncio (no more blocking calls or background threads in the event loop)
- Consolidated state handling into a single DataUpdateCoordinator
- Battery data moved from cover attributes to diagnostic sensor entities
- Config flow now verifies the device responds before creating an entry, and updates the stored IP when re-adding a known shade
- Added translations, proper service error reporting, and HACS metadata

### 0.1.0
- Initial release
- Basic cover and button platform support
- UDP communication implementation
- Config flow integration 
