"""Global fixtures for yandex_smart_home integration."""
import asyncio
import logging
from unittest.mock import patch

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.demo.binary_sensor import DemoBinarySensor
from homeassistant.components.demo.light import DemoLight
from homeassistant.components.demo.sensor import DemoSensor
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfTemperature
from homeassistant.helpers import entityfilter
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.syrupy import HomeAssistantSnapshotExtension
from syrupy import SnapshotAssertion

from custom_components.yandex_smart_home import DOMAIN, ConnectionType, const
from custom_components.yandex_smart_home.config_flow import ConfigFlowHandler

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def enable_custom_integrations(enable_custom_integrations):
    return enable_custom_integrations


@pytest.fixture(autouse=True)
def debug_logging():
    logging.getLogger("custom_components.yandex_smart_home").setLevel(logging.DEBUG)


@pytest.fixture(name="skip_notifications", autouse=True)
def skip_notifications_fixture():
    """Skip notification calls."""
    with patch("homeassistant.components.persistent_notification.async_create"), patch(
        "homeassistant.components.persistent_notification.async_dismiss"
    ):
        yield


@pytest.fixture
def socket_enabled(socket_enabled):
    """Mark socket_enabled as fixture."""
    return socket_enabled


@pytest.fixture
def aiohttp_client(aiohttp_client, socket_enabled):
    """Return aiohttp_client and allow opening sockets."""
    return aiohttp_client


@pytest.fixture
def snapshot(snapshot: SnapshotAssertion) -> SnapshotAssertion:
    """Return snapshot assertion fixture with the Home Assistant extension."""
    return snapshot.use_extension(HomeAssistantSnapshotExtension)


@pytest.fixture
def config_entry_direct():
    return MockConfigEntry(
        domain=DOMAIN,
        version=ConfigFlowHandler.VERSION,
        data={const.CONF_CONNECTION_TYPE: ConnectionType.DIRECT},
        options={const.CONF_FILTER: {entityfilter.CONF_INCLUDE_ENTITY_GLOBS: ["*"]}},
    )


@pytest.fixture()
def config_entry_cloud():
    return MockConfigEntry(
        domain=DOMAIN,
        version=ConfigFlowHandler.VERSION,
        data={
            const.CONF_CONNECTION_TYPE: ConnectionType.CLOUD,
            const.CONF_CLOUD_INSTANCE: {
                const.CONF_CLOUD_INSTANCE_ID: "i-test",
                const.CONF_CLOUD_INSTANCE_CONNECTION_TOKEN: "token-foo",
            },
        },
        options={const.CONF_FILTER: {entityfilter.CONF_INCLUDE_ENTITY_GLOBS: ["*"]}},
    )


@pytest.fixture
def hass_platform(hass):
    demo_sensor = DemoSensor(
        "outside_temp",
        "Outside Temperature",
        state=15.6,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        unit_of_measurement=UnitOfTemperature.CELSIUS,
        battery=None,
    )
    demo_sensor.hass = hass
    demo_sensor.entity_id = "sensor.outside_temp"
    demo_sensor._attr_name = "Температура за бортом"

    demo_binary_sensor = DemoBinarySensor(
        "front_door",
        "Front Door",
        state=True,
        device_class=BinarySensorDeviceClass.DOOR,
    )
    demo_binary_sensor.hass = hass
    demo_binary_sensor.entity_id = "binary_sensor.front_door"
    demo_binary_sensor._attr_name = "Front Door"

    demo_light = DemoLight(
        "light_kitchen",
        "Kitchen Light",
        available=True,
        state=True,
    )
    demo_light.hass = hass
    demo_light.entity_id = "light.kitchen"
    demo_light._attr_name = "Kitchen Light"
    demo_light._ct = 240

    demo_sensor.async_write_ha_state()
    demo_binary_sensor.async_write_ha_state()
    demo_light.async_write_ha_state()

    return hass


@pytest.fixture
def hass_platform_direct(hass_platform, event_loop: asyncio.AbstractEventLoop, config_entry_direct):
    config_entry_direct.add_to_hass(hass_platform)
    event_loop.run_until_complete(hass_platform.config_entries.async_setup(config_entry_direct.entry_id))
    event_loop.run_until_complete(hass_platform.async_block_till_done())

    return hass_platform
