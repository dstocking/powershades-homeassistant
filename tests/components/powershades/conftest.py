"""Fixtures for PowerShades config flow tests."""

from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def mock_setup_entry():
    """Avoid connecting to a real device when an entry is created."""
    with (
        patch("custom_components.powershades.async_setup_entry", return_value=True),
        patch(
            "custom_components.powershades.discovery.async_discover_devices",
            return_value=[],
        ),
    ):
        yield


@pytest.fixture
def mock_discover_devices():
    """Mock broadcast discovery, returning no devices by default."""
    with patch(
        "custom_components.powershades.config_flow.async_discover_devices",
        return_value=[],
    ) as mock:
        yield mock


@pytest.fixture
def mock_device_info():
    """Mock probing a device for its serial number and name."""
    with patch(
        "custom_components.powershades.config_flow.async_get_device_info",
        return_value={"serial": 12345, "name": "Bedroom Shade", "model": 1},
    ) as mock:
        yield mock
