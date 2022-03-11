from __future__ import annotations

from unittest.mock import patch

from homeassistant import config_entries, data_entry_flow
from homeassistant.config import YAML_CONFIG_FILE
from pytest_homeassistant_custom_component.common import MockConfigEntry, patch_yaml_files

from custom_components.yandex_smart_home import cloud, const
from custom_components.yandex_smart_home.config_flow import DOMAIN

COMPONENT_PATH = 'custom_components.yandex_smart_home'


def _mock_config_entry_with_options_populated(data: dict):
    if data[const.CONF_CONNECTION_TYPE] == const.CONNECTION_TYPE_CLOUD:
        data[const.CONF_CLOUD_INSTANCE] = {
            const.CONF_CLOUD_INSTANCE_ID: 'test',
            const.CONF_CLOUD_INSTANCE_PASSWORD: 'secret',
            const.CONF_CLOUD_INSTANCE_CONNECTION_TOKEN: 'foo',
        }

    return MockConfigEntry(
        domain=DOMAIN,
        data=data,
        options={
            'filter': {
                'include_domains': [
                    'fan',
                    'humidifier',
                    'vacuum',
                    'media_player',
                    'climate',
                ],
                'exclude_entities': ['climate.front_gate'],
                'include_entities': ['lock.test']
            },
        },
    )


async def test_step_user_cloud(hass, aioclient_mock):
    with patch_yaml_files({YAML_CONFIG_FILE: ''}):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={'source': config_entries.SOURCE_USER}
        )
        assert result['type'] == 'form'
        assert result['step_id'] == 'include_domains'
        assert result['errors'] is None

        result2 = await hass.config_entries.flow.async_configure(result['flow_id'], {
            'include_domains': ['light']
        })
        assert result2['type'] == 'form'
        assert result2['step_id'] == 'connection_type'
        assert result2['errors'] == {}

        aioclient_mock.post(f'{cloud.BASE_API_URL}/instance/register', status=500)
        result3 = await hass.config_entries.flow.async_configure(result2['flow_id'], {
            const.CONF_CONNECTION_TYPE: const.CONNECTION_TYPE_CLOUD
        })
        assert result3['type'] == 'form'
        assert result3['step_id'] == 'connection_type'
        assert result3['errors']['base'] == 'cannot_connect'

        aioclient_mock.post(f'{cloud.BASE_API_URL}/instance/register', side_effect=Exception())
        result4 = await hass.config_entries.flow.async_configure(result3['flow_id'], {
            const.CONF_CONNECTION_TYPE: const.CONNECTION_TYPE_CLOUD
        })
        assert result4['type'] == 'form'
        assert result4['step_id'] == 'connection_type'
        assert result4['errors']['base'] == 'cannot_connect'

        aioclient_mock.clear_requests()
        aioclient_mock.post(
            f'{cloud.BASE_API_URL}/instance/register',
            status=202,
            json={'id': 'test', 'password': 'simple', 'connection_token': 'foo'},
        )
        result5 = await hass.config_entries.flow.async_configure(result4['flow_id'], {
            const.CONF_CONNECTION_TYPE: const.CONNECTION_TYPE_CLOUD
        })
        assert result5['type'] == 'form'
        assert result5['step_id'] == 'cloud_info'
        assert result5['errors'] is None

        with patch(f'{COMPONENT_PATH}.async_setup', return_value=True) as mock_setup, patch(
                f'{COMPONENT_PATH}.async_setup_entry', return_value=True) as mock_setup_entry:
            result6 = await hass.config_entries.flow.async_configure(result5['flow_id'], {})
            await hass.async_block_till_done()

            assert result6['type'] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
            assert result6['data'] == {
                'connection_type': 'cloud',
                'beta': False,
                'pressure_unit': 'mmHg',
                'devices_discovered': False,
                'cloud_instance': {
                    'id': 'test',
                    'password': 'simple',
                    'token': 'foo'
                },
                'filter': {
                    'exclude_entities': [],
                    'include_domains': ['light'],
                    'include_entities': []
                },
            }

            mock_setup.assert_called_once()
            mock_setup_entry.assert_called_once()


async def test_step_user_with_yaml_filters(hass):
    with patch_yaml_files({YAML_CONFIG_FILE: """
yandex_smart_home:
  filter:
    include_domains:
      - script"""}):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={'source': config_entries.SOURCE_USER}
        )
        assert result['type'] == 'form'
        assert result['step_id'] == 'connection_type'
        assert result['errors'] == {}

        with patch(f'{COMPONENT_PATH}.async_setup', return_value=True) as mock_setup, patch(
                f'{COMPONENT_PATH}.async_setup_entry', return_value=True) as mock_setup_entry:
            result2 = await hass.config_entries.flow.async_configure(result['flow_id'], {
                const.CONF_CONNECTION_TYPE: const.CONNECTION_TYPE_DIRECT
            })
            assert result2['type'] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
            mock_setup.assert_called_once()
            mock_setup_entry.assert_called_once()

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={'source': config_entries.SOURCE_USER}
        )
        assert result['type'] == 'abort'
        assert result['reason'] == 'single_instance_allowed'


async def test_step_user_direct(hass):
    with patch_yaml_files({YAML_CONFIG_FILE: ''}):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={'source': config_entries.SOURCE_USER}
        )
        assert result['type'] == 'form'
        assert result['step_id'] == 'include_domains'
        assert result['errors'] is None

        result2 = await hass.config_entries.flow.async_configure(result['flow_id'], {
            'include_domains': ['light']
        })
        assert result2['type'] == 'form'
        assert result2['step_id'] == 'connection_type'
        assert result2['errors'] == {}

        with patch(f'{COMPONENT_PATH}.async_setup', return_value=True) as mock_setup, patch(
                f'{COMPONENT_PATH}.async_setup_entry', return_value=True) as mock_setup_entry:
            result3 = await hass.config_entries.flow.async_configure(result['flow_id'], {
                const.CONF_CONNECTION_TYPE: const.CONNECTION_TYPE_DIRECT
            })
            await hass.async_block_till_done()

            assert result3['type'] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
            assert result3['data'] == {
                'beta': False,
                'pressure_unit': 'mmHg',
                'connection_type': 'direct',
                'devices_discovered': False,
                'filter': {
                    'exclude_entities': [],
                    'include_domains': ['light'],
                    'include_entities': []
                },
            }

            mock_setup.assert_called_once()
            mock_setup_entry.assert_called_once()


async def test_options_flow_with_yaml_filters_direct(hass):
    config_entry = _mock_config_entry_with_options_populated({
        const.CONF_CONNECTION_TYPE: const.CONNECTION_TYPE_DIRECT,
        const.CONF_FILTER_FROM_YAML: {
            'include_domains': ['script']
        }
    })
    config_entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result['type'] == data_entry_flow.RESULT_TYPE_FORM
    assert result['step_id'] == 'include_domains_yaml'

    result2 = await hass.config_entries.options.async_configure(result['flow_id'], user_input={})
    assert result2['type'] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY


async def test_options_flow_with_yaml_filters_cloud(hass, hass_admin_user, hass_read_only_user):
    config_entry = _mock_config_entry_with_options_populated({
        const.CONF_CONNECTION_TYPE: const.CONNECTION_TYPE_CLOUD,
        const.CONF_FILTER_FROM_YAML: {
            'include_domains': ['script']
        }
    })

    config_entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result['type'] == data_entry_flow.RESULT_TYPE_FORM
    assert result['step_id'] == 'include_domains_yaml'

    result2 = await hass.config_entries.options.async_configure(result['flow_id'], user_input={})
    assert result2['type'] == data_entry_flow.RESULT_TYPE_FORM
    assert result2['step_id'] == 'cloud_settings'
    assert len(result2['data_schema'].schema['user_id'].container) == 1

    result3 = await hass.config_entries.options.async_configure(result2['flow_id'], user_input={
        'user_id': hass_admin_user.id
    })
    assert result3['type'] == data_entry_flow.RESULT_TYPE_FORM
    assert result3['step_id'] == 'cloud_info'

    result4 = await hass.config_entries.options.async_configure(result3['flow_id'], user_input={})
    assert result4['type'] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
    assert config_entry.options['user_id'] == hass_admin_user.id


async def test_options_flow_filter_exclude(hass):
    config_entry = _mock_config_entry_with_options_populated({
        const.CONF_CONNECTION_TYPE: const.CONNECTION_TYPE_DIRECT,
    })
    config_entry.add_to_hass(hass)

    hass.states.async_set('climate.old', 'off')
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(config_entry.entry_id)

    assert result['type'] == data_entry_flow.RESULT_TYPE_FORM
    assert result['step_id'] == 'include_domains'

    result = await hass.config_entries.options.async_configure(result['flow_id'], user_input={
        'domains': ['fan', 'vacuum', 'climate']
    })
    assert result['type'] == data_entry_flow.RESULT_TYPE_FORM
    assert result['step_id'] == 'include_exclude'

    result2 = await hass.config_entries.options.async_configure(result['flow_id'], user_input={
        'entities': ['climate.old'], 'include_exclude_mode': 'exclude'
    })
    assert result2['type'] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
    assert config_entry.options == {
        'filter': {
            'exclude_entities': ['climate.old'],
            'include_domains': ['fan', 'vacuum', 'climate'],
            'include_entities': []
        },
    }


async def test_options_flow_filter_include(hass):
    config_entry = _mock_config_entry_with_options_populated({
        const.CONF_CONNECTION_TYPE: const.CONNECTION_TYPE_DIRECT,
    })
    config_entry.add_to_hass(hass)

    hass.states.async_set('climate.old', 'off')
    hass.states.async_set('climate.new', 'off')

    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(config_entry.entry_id)

    assert result['type'] == data_entry_flow.RESULT_TYPE_FORM
    assert result['step_id'] == 'include_domains'

    result = await hass.config_entries.options.async_configure(result['flow_id'], user_input={
        'domains': ['fan', 'vacuum', 'climate']
    })

    assert result['type'] == data_entry_flow.RESULT_TYPE_FORM
    assert result['step_id'] == 'include_exclude'

    result2 = await hass.config_entries.options.async_configure(result['flow_id'], user_input={
        'entities': ['climate.new'],
        'include_exclude_mode': 'include'
    })
    assert result2['type'] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
    assert config_entry.options == {
        'filter': {
            'exclude_entities': [],
            'include_domains': ['fan', 'vacuum'],
            'include_entities': ['climate.new'],
        }
    }


async def test_options_flow_filter_exclude2(hass):
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            'connection_type': 'direct'
        },
        options={
            'filter': {
                'include_domains': [
                    'fan',
                    'humidifier',
                    'vacuum',
                    'media_player',
                    'climate',
                ],
                'exclude_entities': ['climate.front_gate'],
                'include_entities': []
            },
        },
    )
    config_entry.add_to_hass(hass)

    hass.states.async_set('climate.old', 'off')
    hass.states.async_set('climate.new', 'off')

    await hass.async_block_till_done()

    with patch_yaml_files({YAML_CONFIG_FILE: ''}):
        result = await hass.config_entries.options.async_init(config_entry.entry_id)

        assert result['type'] == data_entry_flow.RESULT_TYPE_FORM
        assert result['step_id'] == 'include_domains'

        result = await hass.config_entries.options.async_configure(result['flow_id'], user_input={
            'domains': ['fan', 'vacuum', 'climate']
        })

        assert result['type'] == data_entry_flow.RESULT_TYPE_FORM
        assert result['step_id'] == 'include_exclude'

        result2 = await hass.config_entries.options.async_configure(result['flow_id'], user_input={
            'entities': ['climate.new'],
            'include_exclude_mode': 'include'
        })
        assert result2['type'] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
        assert config_entry.options == {
            'filter': {
                'exclude_entities': [],
                'include_domains': ['fan', 'vacuum'],
                'include_entities': ['climate.new'],
            }
        }


async def test_options_flow_with_non_existant_entity(hass):
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            'connection_type': 'direct'
        },
        options={
            'filter': {
                'include_domains': [],
                'include_entities': ['climate.not_exist', 'climate.front_gate'],
            },
        },
    )
    config_entry.add_to_hass(hass)
    hass.states.async_set('climate.front_gate', 'off')
    hass.states.async_set('climate.new', 'off')

    await hass.async_block_till_done()

    with patch_yaml_files({YAML_CONFIG_FILE: ''}):
        result = await hass.config_entries.options.async_init(config_entry.entry_id)

        assert result['type'] == data_entry_flow.RESULT_TYPE_FORM
        assert result['step_id'] == 'include_domains'

        result2 = await hass.config_entries.options.async_configure(result['flow_id'], user_input={
            'domains': ['fan', 'vacuum', 'climate']
        })

        assert result2['type'] == data_entry_flow.RESULT_TYPE_FORM
        assert result2['step_id'] == 'include_exclude'
        entities = result2['data_schema']({'include_exclude_mode': 'include'})['entities']

        print(entities)
        assert 'climate.not_exist' not in entities

        result3 = await hass.config_entries.options.async_configure(result2['flow_id'], user_input={
                'entities': ['climate.new', 'climate.front_gate'],
                'include_exclude_mode': 'include',
            }
        )
        assert result3['type'] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
        assert config_entry.options == {
            'filter': {
                'exclude_entities': [],
                'include_domains': ['fan', 'vacuum'],
                'include_entities': ['climate.new', 'climate.front_gate'],
            },
        }
