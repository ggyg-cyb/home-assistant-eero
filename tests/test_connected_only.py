"""Signal sensors turn unavailable while eero lists a client as offline.

eero keeps listing a client for a while after it disconnects, with
connected=false and the last signal it saw. Without connected_only the sensor
kept showing that stale reading for hours.

Run with pytest-homeassistant-custom-component installed:
    pytest tests/test_connected_only.py
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from custom_components.eero.api.client import EeroClient  # noqa: E402
from custom_components.eero.const import (  # noqa: E402
    CONF_PREFIX_NETWORK_NAME,
    CONF_SUFFIX_CONNECTION_TYPE,
)
from custom_components.eero.sensor import (  # noqa: E402
    SENSOR_DESCRIPTIONS,
    EeroSensorEntity,
)

NETWORK_URL = "/2.2/networks/1"
CLIENT_ID = "client-a"
SIGNAL = next(d for d in SENSOR_DESCRIPTIONS if d.key == "signal")


def make_entity(clients: list[dict]) -> EeroSensorEntity:
    network = SimpleNamespace(id="1", url=NETWORK_URL, resources=[])
    network.resources = [EeroClient(None, network, data) for data in clients]
    coordinator = MagicMock()
    coordinator.last_update_success = True
    coordinator.data.networks = [network]
    return EeroSensorEntity(
        coordinator,
        "1",
        CLIENT_ID,
        SIGNAL,
        {CONF_PREFIX_NETWORK_NAME: False, CONF_SUFFIX_CONNECTION_TYPE: False},
    )


def client(connected: bool, signal: str) -> dict:
    return {
        "url": f"{NETWORK_URL}/devices/{CLIENT_ID}",
        "connected": connected,
        "connectivity": {"signal": signal},
    }


def test_signal_description_is_connected_only():
    assert SIGNAL.connected_only is True


def test_connected_client_is_available_with_value():
    entity = make_entity([client(True, "-60 dBm")])
    assert entity.available is True
    assert entity.native_value == -60
    assert entity.native_unit_of_measurement == "dBm"


def test_offline_client_is_unavailable_and_keeps_unit():
    entity = make_entity([client(False, "-82 dBm")])
    assert entity.available is False
    assert entity.native_unit_of_measurement == "dBm"


def test_departed_client_is_unavailable():
    entity = make_entity([client(True, "-60 dBm")])
    assert entity.available is True
    entity.coordinator.data.networks[0].resources = []
    assert entity.available is False


def test_other_sensors_ignore_connected():
    other = next(d for d in SENSOR_DESCRIPTIONS if not d.connected_only)
    entity = make_entity([client(False, "-82 dBm")])
    entity.entity_description = other
    assert entity.available is True
