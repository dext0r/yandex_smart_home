"""Global fixtures for yandex_smart_home integration."""
import asyncio
from unittest.mock import patch

from homeassistant.components import http
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.demo.binary_sensor import DemoBinarySensor
from homeassistant.components.demo.light import DemoLight
from homeassistant.components.demo.sensor import DemoSensor
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfTemperature
from homeassistant.helpers import entityfilter
from homeassistant.setup import async_setup_component
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry, MockUser

from custom_components import yandex_smart_home
from custom_components.yandex_smart_home import DOMAIN, async_setup, async_setup_entry, const

pytest_plugins = "pytest_homeassistant_custom_component"


def pytest_configure(*_):
    yandex_smart_home._PYTEST = True


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


@pytest.fixture(name="skip_notifications", autouse=True)
def skip_notifications_fixture():
    """Skip notification calls."""
    with patch("homeassistant.components.persistent_notification.async_create"), patch(
        "homeassistant.components.persistent_notification.async_dismiss"
    ):
        yield


@pytest.fixture
def config_entry():
    return MockConfigEntry(domain=DOMAIN, options={const.CONF_FILTER: {entityfilter.CONF_INCLUDE_ENTITY_GLOBS: ["*"]}})


@pytest.fixture
def config_entry_with_notifier(hass_admin_user: MockUser):
    return MockConfigEntry(
        domain=DOMAIN,
        data={
            const.CONF_NOTIFIER: [
                {
                    const.CONF_NOTIFIER_OAUTH_TOKEN: "",
                    const.CONF_NOTIFIER_SKILL_ID: "",
                    const.CONF_NOTIFIER_USER_ID: hass_admin_user.id,
                }
            ]
        },
    )


@pytest.fixture()
def config_entry_cloud_connection():
    return MockConfigEntry(
        domain=DOMAIN,
        data={
            const.CONF_CONNECTION_TYPE: const.CONNECTION_TYPE_CLOUD,
            const.CONF_DEVICES_DISCOVERED: False,
            const.CONF_CLOUD_INSTANCE: {
                const.CONF_CLOUD_INSTANCE_ID: "test",
                const.CONF_CLOUD_INSTANCE_CONNECTION_TOKEN: "foo",
            },
        },
        options={const.CONF_FILTER: {entityfilter.CONF_INCLUDE_ENTITY_GLOBS: ["*"]}},
    )


@pytest.fixture
def hass_platform(event_loop: asyncio.AbstractEventLoop, hass, config_entry):
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
    demo_sensor._attr_name = "Outside Temperature"

    demo_light = DemoLight(
        "light_kitchen",
        "Kitchen Light",
        available=True,
        state=True,
    )
    demo_light.hass = hass
    demo_light.entity_id = "light.kitchen"
    demo_light._attr_name = "Kitchen Light"

    demo_sensor.async_write_ha_state()
    demo_light.async_write_ha_state()

    event_loop.run_until_complete(async_setup_component(hass, http.DOMAIN, {http.DOMAIN: {}}))

    config_entry.add_to_hass(hass)
    with patch.object(hass.config_entries.flow, "async_init", return_value=None):
        event_loop.run_until_complete(async_setup(hass, {}))
        event_loop.run_until_complete(async_setup_entry(hass, config_entry))

    return hass


@pytest.fixture
def hass_platform_cloud_connection(event_loop: asyncio.AbstractEventLoop, hass, config_entry_cloud_connection):
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
    demo_sensor._attr_name = "Outside Temperature"

    demo_binary_sensor = DemoBinarySensor(
        "front_door",
        "Front Door",
        state=True,
        device_class=BinarySensorDeviceClass.DOOR,
    )
    demo_binary_sensor.hass = hass
    demo_binary_sensor.entity_id = "binary_sensor.front_Door"
    demo_binary_sensor._attr_name = "Front Door"

    demo_light = DemoLight(
        "light_kitchen",
        "Kitchen Light",
        ct=240,
        available=True,
        state=True,
    )
    demo_light.hass = hass
    demo_light.entity_id = "light.kitchen"
    demo_light._attr_name = "Kitchen Light"

    demo_sensor.async_write_ha_state()
    demo_binary_sensor.async_write_ha_state()
    demo_light.async_write_ha_state()

    event_loop.run_until_complete(async_setup_component(hass, http.DOMAIN, {http.DOMAIN: {}}))

    config_entry_cloud_connection.add_to_hass(hass)
    event_loop.run_until_complete(async_setup(hass, {}))
    with patch("custom_components.yandex_smart_home.cloud.CloudManager.connect", return_value=None):
        event_loop.run_until_complete(async_setup_entry(hass, config_entry_cloud_connection))
        event_loop.run_until_complete(hass.async_block_till_done())

    return hass
