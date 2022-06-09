from unittest.mock import patch

from homeassistant.components import http
from homeassistant.config import YAML_CONFIG_FILE
from homeassistant.const import SERVICE_RELOAD
from homeassistant.core import Context
from homeassistant.exceptions import Unauthorized
from homeassistant.helpers.reload import async_integration_yaml_config
from homeassistant.setup import async_setup_component
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry, load_fixture, patch_yaml_files

from custom_components.yandex_smart_home import (
    CLOUD_MANAGER,
    CONFIG,
    DOMAIN,
    NOTIFIERS,
    async_remove_entry,
    async_setup,
    async_setup_entry,
    async_unload_entry,
    cloud,
    const,
)


async def test_bad_config(hass):
    with patch_yaml_files({YAML_CONFIG_FILE: 'yandex_smart_home:\n  bad: true'}):
        assert await async_integration_yaml_config(hass, DOMAIN) is None


async def test_valid_config(hass):
    with patch_yaml_files({YAML_CONFIG_FILE: load_fixture('valid-config.yaml')}):
        config = await async_integration_yaml_config(hass, DOMAIN)

    assert DOMAIN in config
    assert config[DOMAIN].keys() == {'notifier', 'settings', 'filter', 'entity_config', 'color_profile'}


async def test_empty_dict_config(hass):
    files = {YAML_CONFIG_FILE: """
yandex_smart_home:
  settings:
  entity_config:
"""}
    with patch_yaml_files(files):
        config = await async_integration_yaml_config(hass, DOMAIN)

    assert DOMAIN in config
    assert isinstance(config[DOMAIN]['settings'], dict)
    assert config[DOMAIN]['entity_config'] == {}


async def test_reload(hass, hass_admin_user, hass_read_only_user, config_entry):
    await async_setup_component(hass, http.DOMAIN, {http.DOMAIN: {}})
    config_entry.add_to_hass(hass)

    assert await async_setup(hass, {})
    assert await async_setup_entry(hass, config_entry)

    assert not hass.data[DOMAIN][CONFIG].get_entity_config('sensor.not_existed')

    files = {YAML_CONFIG_FILE: """
yandex_smart_home:
  entity_config:
    sensor.test:
      name: Test
"""}
    with patch('custom_components.yandex_smart_home.async_setup', return_value=True), patch_yaml_files(files):
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


async def test_setup_component(hass):
    await async_setup_component(hass, http.DOMAIN, {http.DOMAIN: {}})

    with patch_yaml_files({YAML_CONFIG_FILE: load_fixture('valid-config.yaml')}):
        config = await async_integration_yaml_config(hass, DOMAIN)

    with patch.object(hass.config_entries.flow, 'async_init', return_value=None):
        assert await async_setup(hass, config)

    assert hass.data[DOMAIN][CONFIG] is None


async def test_async_setup_entry(hass, config_entry_with_notifier):
    await async_setup_component(hass, http.DOMAIN, {http.DOMAIN: {}})
    config_entry_with_notifier.add_to_hass(hass)

    assert await async_setup(hass, {})
    assert await async_setup_entry(hass, config_entry_with_notifier)

    assert len(hass.data[DOMAIN][CONFIG].notifier) == 0
    assert const.CONF_PRESSURE_UNIT in config_entry_with_notifier.options


async def test_async_setup_entry_filters(hass):
    await async_setup_component(hass, http.DOMAIN, {http.DOMAIN: {}})

    entry_with_filters = MockConfigEntry(
        domain=DOMAIN,
        options={
            const.CONF_FILTER: {
                'include_domains': [
                    'media_player',
                    'climate',
                ],
                'exclude_entities': ['climate.front_gate'],
            },
        },
    )
    entry_with_filters.add_to_hass(hass)

    with patch_yaml_files({YAML_CONFIG_FILE: ''}):
        assert await async_setup(hass, await async_integration_yaml_config(hass, DOMAIN))
        assert await async_setup_entry(hass, entry_with_filters)

        assert hass.data[DOMAIN][CONFIG].should_expose('media_player.test') is True
        assert hass.data[DOMAIN][CONFIG].should_expose('climate.test') is True
        assert hass.data[DOMAIN][CONFIG].should_expose('climate.front_gate') is False

    with patch_yaml_files({YAML_CONFIG_FILE: 'yandex_smart_home:'}):
        assert await async_setup(hass, await async_integration_yaml_config(hass, DOMAIN))
        assert await async_setup_entry(hass, entry_with_filters)

        assert hass.data[DOMAIN][CONFIG].should_expose('media_player.test') is True
        assert hass.data[DOMAIN][CONFIG].should_expose('climate.test') is True
        assert hass.data[DOMAIN][CONFIG].should_expose('climate.front_gate') is False

    with patch_yaml_files({YAML_CONFIG_FILE: """
yandex_smart_home:
  filter:
    include_domains:
      - light"""}):
        assert await async_setup(hass, await async_integration_yaml_config(hass, DOMAIN))
        assert await async_setup_entry(hass, entry_with_filters)

        assert hass.data[DOMAIN][CONFIG].should_expose('light.test') is True
        assert hass.data[DOMAIN][CONFIG].should_expose('climate.test') is False


async def test_async_setup_entry_cloud(hass, config_entry_cloud_connection):
    await async_setup_component(hass, http.DOMAIN, {http.DOMAIN: {}})

    assert await async_setup(hass, {})

    with patch(
            'custom_components.yandex_smart_home.cloud.BASE_API_URL', return_value=None
    ):
        assert await async_setup_entry(hass, config_entry_cloud_connection)

    await hass.async_block_till_done()

    # assert len(hass.data[DOMAIN][CONFIG].notifier) == 1  # TODO: fix
    assert hass.data[DOMAIN][CLOUD_MANAGER] is not None

    await async_unload_entry(hass, config_entry_cloud_connection)
    await hass.async_block_till_done()

    assert hass.data[DOMAIN][CLOUD_MANAGER] is None


async def test_async_unload_entry(hass, config_entry_with_notifier):
    await async_setup_component(hass, http.DOMAIN, {http.DOMAIN: {}})
    config_entry_with_notifier.add_to_hass(hass)

    assert await async_setup(hass, {})
    assert await async_setup_entry(hass, config_entry_with_notifier)
    await async_unload_entry(hass, config_entry_with_notifier)

    assert hass.data[DOMAIN][CONFIG] is None
    assert len(hass.data[DOMAIN][NOTIFIERS]) == 0


async def test_async_remove_entry_cloud(hass, config_entry_cloud_connection, aioclient_mock, caplog):
    aioclient_mock.delete(f'{cloud.BASE_API_URL}/instance/test', status=500)
    await async_remove_entry(hass, config_entry_cloud_connection)
    assert aioclient_mock.call_count == 1
    assert len(caplog.records) == 1
    assert 'Failed to delete' in caplog.records[0].message

    aioclient_mock.clear_requests()
    caplog.clear()

    aioclient_mock.delete(f'{cloud.BASE_API_URL}/instance/test', status=200)
    await async_remove_entry(hass, config_entry_cloud_connection)
    (method, url, data, headers) = aioclient_mock.mock_calls[0]
    assert headers == {'Authorization': 'Bearer foo'}

    assert aioclient_mock.call_count == 1
    assert len(caplog.records) == 0


async def test_async_setup_update_from_yaml(hass, hass_admin_user):
    await async_setup_component(hass, http.DOMAIN, {http.DOMAIN: {}})

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            const.CONF_NOTIFIER: [{
                const.CONF_NOTIFIER_OAUTH_TOKEN: 'entry',
                const.CONF_NOTIFIER_SKILL_ID: 'entry',
                const.CONF_NOTIFIER_USER_ID: hass_admin_user.id,
            }],
        }
    )
    entry.add_to_hass(hass)

    assert await async_setup(hass, {})
    assert await async_setup_entry(hass, entry)

    assert entry.data == {
        'connection_type': 'direct',
        'devices_discovered': True,
    }
    assert entry.options == {
        'beta': False,
        'cloud_stream': False,
        'pressure_unit': 'mmHg'
    }

    with patch_yaml_files({YAML_CONFIG_FILE: f"""
yandex_smart_home:
  settings:
    pressure_unit: pa
  notifier:
    oauth_token: yaml
    skill_id: yaml
    user_id: {hass_admin_user.id}"""}):
        assert await async_setup(hass, await async_integration_yaml_config(hass, DOMAIN))
        with patch('custom_components.yandex_smart_home.async_setup', return_value=True):
            assert await async_setup_entry(hass, entry)

    assert entry.data[const.CONF_NOTIFIER][0][const.CONF_NOTIFIER_OAUTH_TOKEN] == 'yaml'
    assert entry.options[const.CONF_PRESSURE_UNIT] == 'pa'


async def test_async_setup_update_from_yaml_checksum(hass, hass_admin_user):
    await async_setup_component(hass, http.DOMAIN, {http.DOMAIN: {}})

    entry = MockConfigEntry(domain=DOMAIN)
    entry.add_to_hass(hass)

    with patch_yaml_files({YAML_CONFIG_FILE: """
yandex_smart_home:
  settings:
    pressure_unit: pa"""}):
        assert await async_setup(hass, await async_integration_yaml_config(hass, DOMAIN))
        assert await async_setup_entry(hass, entry)

    assert entry.data == {
        'connection_type': 'direct',
        'devices_discovered': True,
        'notifier': [],
        'yaml_config_hash': '93c51c44a1036f88197b32160df2ef38'
    }
    assert entry.options == {
        'beta': False,
        'cloud_stream': False,
        'pressure_unit': 'pa',
        'color_profile': {}
    }

    with patch_yaml_files({YAML_CONFIG_FILE: """
yandex_smart_home:
  entity_config:
    switch.test:
      turn_on:
        service: switch.turn_on
        data:
          entity_id: 'switch.test_{{ 1 + 2 }}'
  settings:
    pressure_unit: mmHg
"""}):
        assert await async_setup(hass, await async_integration_yaml_config(hass, DOMAIN))
        with patch('custom_components.yandex_smart_home.async_setup', return_value=True):
            assert await async_setup_entry(hass, entry)

    assert entry.options[const.CONF_PRESSURE_UNIT] == 'mmHg'
    assert entry.data[const.YAML_CONFIG_HASH] == 'cbe26e947d35ed6222f97e493b32d94f'
