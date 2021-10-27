"""Global fixtures for yandex_smart_home integration."""
from unittest.mock import patch

from homeassistant.components import http
from homeassistant.components.demo.light import DemoLight
from homeassistant.components.demo.sensor import DemoSensor
from homeassistant.components.sensor import STATE_CLASS_MEASUREMENT
from homeassistant.config import YAML_CONFIG_FILE
from homeassistant.const import DEVICE_CLASS_TEMPERATURE, TEMP_CELSIUS
from homeassistant.setup import async_setup_component
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry, patch_yaml_files

from custom_components.yandex_smart_home import DOMAIN, async_setup, async_setup_entry, const

pytest_plugins = 'pytest_homeassistant_custom_component'


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


@pytest.fixture
def config_entry():
    return MockConfigEntry(domain=DOMAIN)


@pytest.fixture
def config_entry_with_notifier(hass_admin_user):
    return MockConfigEntry(domain=DOMAIN, data={const.CONF_NOTIFIER: [{
        const.CONF_NOTIFIER_OAUTH_TOKEN: '',
        const.CONF_NOTIFIER_SKILL_ID: '',
        const.CONF_NOTIFIER_USER_ID: hass_admin_user.id,
    }]})


@pytest.fixture()
def config_entry_cloud_connection():
    return MockConfigEntry(domain=DOMAIN, data={
        const.CONF_CONNECTION_TYPE: const.CONNECTION_TYPE_CLOUD,
        const.CONF_DEVICES_DISCOVERED: False,
        const.CONF_CLOUD_INSTANCE: {
            const.CONF_CLOUD_INSTANCE_ID: 'test',
            const.CONF_CLOUD_INSTANCE_CONNECTION_TOKEN: 'foo',

        }
    })


@pytest.fixture
def hass_platform(loop, hass, config_entry):
    demo_sensor = DemoSensor(
        unique_id='outside_temp',
        name='Outside Temperature',
        state=15.6,
        device_class=DEVICE_CLASS_TEMPERATURE,
        state_class=STATE_CLASS_MEASUREMENT,
        unit_of_measurement=TEMP_CELSIUS,
        battery=None
    )
    demo_sensor.hass = hass
    demo_sensor.entity_id = 'sensor.outside_temp'

    demo_light = DemoLight(
        unique_id='light_kitchen',
        name='Kitchen Light',
        available=True,
        state=True,
    )
    demo_light.hass = hass
    demo_light.entity_id = 'light.kitchen'

    loop.run_until_complete(
        demo_sensor.async_update_ha_state()
    )
    loop.run_until_complete(
        demo_light.async_update_ha_state()
    )

    loop.run_until_complete(
        async_setup_component(hass, http.DOMAIN, {http.DOMAIN: {}})
    )
    loop.run_until_complete(
        hass.async_block_till_done()
    )

    with patch.object(hass.config_entries.flow, 'async_init', return_value=None), patch_yaml_files({
        YAML_CONFIG_FILE: 'yandex_smart_home:'
    }):
        loop.run_until_complete(async_setup(hass, {DOMAIN: {}}))
        loop.run_until_complete(async_setup_entry(hass, config_entry))

    return hass


@pytest.fixture
def hass_platform_cloud_connection(loop, hass, config_entry_cloud_connection):
    demo_sensor = DemoSensor(
        unique_id='outside_temp',
        name='Outside Temperature',
        state=15.6,
        device_class=DEVICE_CLASS_TEMPERATURE,
        state_class=STATE_CLASS_MEASUREMENT,
        unit_of_measurement=TEMP_CELSIUS,
        battery=None
    )
    demo_sensor.hass = hass
    demo_sensor.entity_id = 'sensor.outside_temp'

    demo_light = DemoLight(
        unique_id='light_kitchen',
        name='Kitchen Light',
        available=True,
        state=True,
    )
    demo_light.hass = hass
    demo_light.entity_id = 'light.kitchen'

    loop.run_until_complete(
        demo_sensor.async_update_ha_state()
    )
    loop.run_until_complete(
        demo_light.async_update_ha_state()
    )

    loop.run_until_complete(
        async_setup_component(hass, http.DOMAIN, {http.DOMAIN: {}})
    )
    loop.run_until_complete(
        hass.async_block_till_done()
    )

    with patch.object(hass.config_entries.flow, 'async_init', return_value=None), patch_yaml_files({
        YAML_CONFIG_FILE: 'yandex_smart_home:'
    }):
        config_entry_cloud_connection.add_to_hass(hass)
        loop.run_until_complete(async_setup(hass, {DOMAIN: {}}))
        with patch('custom_components.yandex_smart_home.cloud.CloudManager.connect', return_value=None):
            loop.run_until_complete(async_setup_entry(hass, config_entry_cloud_connection))

    return hass


@pytest.fixture(name='skip_notifications', autouse=True)
def skip_notifications_fixture():
    """Skip notification calls."""
    with patch('homeassistant.components.persistent_notification.async_create'), patch(
        'homeassistant.components.persistent_notification.async_dismiss'
    ):
        yield
