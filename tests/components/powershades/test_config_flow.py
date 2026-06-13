"""Tests for the PowerShades config flow."""

from unittest.mock import patch

from homeassistant.config_entries import SOURCE_DHCP, SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.service_info.dhcp import DhcpServiceInfo

from custom_components.powershades.const import DOMAIN
from custom_components.powershades.udp import PowerShadesTimeoutError

from pytest_homeassistant_custom_component.common import MockConfigEntry

TEST_IP = "192.168.1.50"


async def test_manual_flow_success(
    hass: HomeAssistant, mock_discover_devices, mock_device_info, mock_setup_entry
) -> None:
    """No devices discovered, user enters an IP manually and it works."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "manual"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"ip": TEST_IP}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "PowerShade Bedroom Shade"
    assert result["data"] == {
        "ip": TEST_IP,
        "serial": 12345,
        "name": "Bedroom Shade",
        "model": 1,
    }


async def test_manual_flow_cannot_connect(
    hass: HomeAssistant, mock_discover_devices
) -> None:
    """The device does not respond to the probe."""
    with patch(
        "custom_components.powershades.config_flow.async_get_device_info",
        side_effect=PowerShadesTimeoutError,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"ip": TEST_IP}
        )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "manual"
    assert result["errors"] == {"base": "cannot_connect"}


async def test_manual_flow_invalid_ip(
    hass: HomeAssistant, mock_discover_devices
) -> None:
    """An invalid IPv4 address is rejected before probing the device."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"ip": "not-an-ip"}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "manual"
    assert result["errors"] == {"ip": "invalid_ip"}


async def test_manual_flow_duplicate(
    hass: HomeAssistant, mock_discover_devices
) -> None:
    """A shade with an already-configured IP cannot be added again."""
    entry = MockConfigEntry(domain=DOMAIN, data={"ip": TEST_IP})
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"ip": TEST_IP}
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_discovery_pick_device(
    hass: HomeAssistant, mock_device_info, mock_setup_entry
) -> None:
    """Discovered devices are offered for selection."""
    with patch(
        "custom_components.powershades.config_flow.async_discover_devices",
        return_value=[{"ip": TEST_IP, "serial": 12345, "model": 1}],
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "pick_device"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"device": TEST_IP}
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "PowerShade Bedroom Shade"
    assert result["data"]["ip"] == TEST_IP
    assert result["data"]["serial"] == 12345


async def test_dhcp_discovery(
    hass: HomeAssistant, mock_device_info, mock_setup_entry
) -> None:
    """A device found via DHCP is confirmed and added."""
    discovery_info = DhcpServiceInfo(
        ip=TEST_IP,
        hostname="ps-bedroom",
        macaddress="d83af5112233",
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_DHCP}, data=discovery_info
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "discovery_confirm"

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "PowerShade Bedroom Shade"
    assert result["data"] == {
        "ip": TEST_IP,
        "serial": 12345,
        "name": "Bedroom Shade",
        "mac": "d8:3a:f5:11:22:33",
        "model": 1,
    }
