# PowerShades Home Assistant Integration

A Home Assistant custom integration for controlling PowerShades motorized blinds via UDP communication.

## Features

- **Cover Platform**: Control blinds as Home Assistant covers (open, close, set position)
- **Button Platform**: Additional buttons for specific blind operations
- **UDP Communication**: Direct UDP communication with PowerShades controllers
- **Config Flow**: Easy setup through Home Assistant's UI
- **Local Control**: No cloud dependencies, works entirely locally

## Installation

### HACS Installation (For Unpublished Repositories)

Since this integration is not yet published to HACS, you'll need to add it as a custom repository:

1. In HACS, go to **Settings** → **Repositories**
2. Click the **+** button to add a new repository
3. Enter the repository URL: `https://github.com/yourusername/powershades-homeassistant`
4. Select **Integration** as the category
5. Click **Add**
6. Once added, search for "PowerShades" in HACS
7. Click **Download**
8. Restart Home Assistant

### Manual Installation

1. Download this repository (clone or download ZIP)
2. Copy the `custom_components/powershades` folder to your Home Assistant `config/custom_components/` directory
3. Restart Home Assistant

## Configuration

1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for "PowerShades"
4. Enter your PowerShades controller's IP address and port
5. Configure your blinds

## Usage

### Cover Controls

Once configured, your PowerShades will appear as covers in Home Assistant. You can:

- **Open**: Fully open the blinds
- **Close**: Fully close the blinds  
- **Set Position**: Set blinds to a specific percentage (0-100)
- **Stop**: Stop blinds in their current position

### Button Controls

Additional buttons provide quick access to common operations:

- **Preset Positions**: Quick access to favorite positions
- **Group Operations**: Control multiple blinds simultaneously

## Requirements

- Home Assistant 2023.8.0 or newer
- PowerShades controller with UDP communication enabled

## Supported Devices

This integration supports PowerShades controllers that communicate via UDP protocol.

## Troubleshooting


### Debug Logging

Enable debug logging by adding to your `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.powershades: debug
```

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

### 0.1.0
- Initial release
- Basic cover and button platform support
- UDP communication implementation
- Config flow integration 
