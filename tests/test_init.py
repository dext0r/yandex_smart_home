from unittest.mock import patch

from homeassistant.components import http
from homeassistant.config import YAML_CONFIG_FILE
from homeassistant.core import Context
from homeassistant.exceptions import ConfigEntryNotReady, Unauthorized
from homeassistant.helpers.reload import async_integration_yaml_config
from homeassistant.setup import async_setup_component
import pytest
from pytest_homeassistant_custom_component.common import load_fixture, patch_yaml_files

from custom_components.yandex_smart_home import (
    CONFIG,
    DOMAIN,
    SERVICE_RELOAD,
    async_setup,
    async_setup_entry,
    async_unload_entry,
)


async def test_bad_config(hass):
    with patch_yaml_files({YAML_CONFIG_FILE: 'yandex_smart_home:\n  bad: true'}):
        assert await async_integration_yaml_config(hass, DOMAIN) is None


async def test_invalid_property_type(hass):
    files = {YAML_CONFIG_FILE: """
yandex_smart_home:
  entity_config:
    sensor.test:
      properties:
        - type: invalid
          entity: sensor.test
"""}
    with patch_yaml_files(files):
        assert await async_integration_yaml_config(hass, DOMAIN) is None


async def test_invalid_mode(hass):
    files = {YAML_CONFIG_FILE: """
yandex_smart_home:
  entity_config:
    sensor.test:
      modes:
        fan_speed:
          invalid: ['invalid']
"""}
    with patch_yaml_files(files):
        assert await async_integration_yaml_config(hass, DOMAIN) is None


async def test_invalid_mode_instance(hass):
    files = {YAML_CONFIG_FILE: """
yandex_smart_home:
  entity_config:
    sensor.test:
      modes:
        invalid:
"""}
    with patch_yaml_files(files):
        assert await async_integration_yaml_config(hass, DOMAIN) is None


async def test_invalid_toggle_instance(hass):
    files = {YAML_CONFIG_FILE: """
yandex_smart_home:
  entity_config:
    sensor.test:
      custom_toggles:
        invalid:
"""}
    with patch_yaml_files(files):
        assert await async_integration_yaml_config(hass, DOMAIN) is None


async def test_invalid_range_instance(hass):
    files = {YAML_CONFIG_FILE: """
yandex_smart_home:
  entity_config:
    sensor.test:
      custom_ranges:
        invalid:
"""}
    with patch_yaml_files(files):
        assert await async_integration_yaml_config(hass, DOMAIN) is None


async def test_invalid_pressure_unit(hass):
    files = {YAML_CONFIG_FILE: """
yandex_smart_home:
  settings:
    pressure_unit: invalid
"""}
    with patch_yaml_files(files):
        assert await async_integration_yaml_config(hass, DOMAIN) is None


async def test_valid_config(hass):
    with patch_yaml_files({YAML_CONFIG_FILE: load_fixture('config/valid.yaml')}):
        config = await async_integration_yaml_config(hass, DOMAIN)

    assert DOMAIN in config
    assert config[DOMAIN].keys() == {'notifier', 'settings', 'filter', 'entity_config'}


async def test_setup_component(hass):
    await async_setup_component(hass, http.DOMAIN, {http.DOMAIN: {}})

    with patch_yaml_files({YAML_CONFIG_FILE: load_fixture('config/valid.yaml')}):
        config = await async_integration_yaml_config(hass, DOMAIN)

    with patch.object(hass.config_entries.flow, 'async_init', return_value=None):
        assert await async_setup(hass, config)

    assert hass.data[DOMAIN][CONFIG] is None


async def test_reload(hass, hass_admin_user, hass_read_only_user, config_entry):
    await async_setup_component(hass, http.DOMAIN, {http.DOMAIN: {}})

    with patch.object(hass.config_entries.flow, 'async_init', return_value=None), patch_yaml_files({
        YAML_CONFIG_FILE: 'yandex_smart_home:'
    }):
        assert await async_setup(hass, {})
        assert await async_setup_entry(hass, config_entry)

    assert not hass.data[DOMAIN][CONFIG].get_entity_config('sensor.not_existed')

    files = {YAML_CONFIG_FILE: """
yandex_smart_home:
  entity_config:
    sensor.test:
      name: Test
"""}
    with patch_yaml_files(files):
        with pytest.raises(Unauthorized):
            await hass.services.async_call(
                DOMAIN,
                SERVICE_RELOAD,
                blocking=True,
                context=Context(user_id=hass_read_only_user.id),
            )

        await hass.services.async_call(
            DOMAIN,
            SERVICE_RELOAD,
            blocking=True,
            context=Context(user_id=hass_admin_user.id),
        )
        await hass.async_block_till_done()

    assert hass.data[DOMAIN][CONFIG].get_entity_config('sensor.test').get('name') == 'Test'

    with patch_yaml_files({YAML_CONFIG_FILE: 'yandex_smart_home:\n  invalid: true'}):
        with pytest.raises(ValueError, match='.*invalid.*'):
            await hass.services.async_call(
                DOMAIN,
                SERVICE_RELOAD,
                blocking=True,
                context=Context(user_id=hass_admin_user.id),
            )
        await hass.async_block_till_done()

    await async_unload_entry(hass, config_entry)

    with patch_yaml_files({YAML_CONFIG_FILE: ''}):
        with pytest.raises(ValueError, match='.*not enabled.*'):
            await hass.services.async_call(
                DOMAIN,
                SERVICE_RELOAD,
                blocking=True,
                context=Context(user_id=hass_admin_user.id),
            )
        await hass.async_block_till_done()


async def test_async_setup_entry(hass, config_entry):
    await async_setup_component(hass, http.DOMAIN, {http.DOMAIN: {}})

    with patch.object(hass.config_entries.flow, 'async_init', return_value=None), patch_yaml_files({
        YAML_CONFIG_FILE: ''
    }):
        assert await async_setup(hass, {})

        with pytest.raises(ConfigEntryNotReady):
            assert await async_setup_entry(hass, config_entry)


async def test_async_unload_entry(hass, config_entry):
    await async_setup_component(hass, http.DOMAIN, {http.DOMAIN: {}})

    with patch.object(hass.config_entries.flow, 'async_init', return_value=None), patch_yaml_files({
        YAML_CONFIG_FILE: ''
    }):
        assert await async_setup(hass, {})
        assert await async_unload_entry(hass, config_entry)
