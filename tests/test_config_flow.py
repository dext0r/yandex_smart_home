from unittest.mock import patch

from homeassistant import config_entries, data_entry_flow
from homeassistant.config import YAML_CONFIG_FILE
from pytest_homeassistant_custom_component.common import MockConfigEntry, patch_yaml_files

from custom_components.yandex_smart_home.config_flow import DOMAIN

COMPONENT_PATH = 'custom_components.yandex_smart_home'


def _mock_config_entry_with_options_populated():
    return MockConfigEntry(
        domain=DOMAIN,
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


async def test_step_user_with_yaml_filters(hass):
    with patch_yaml_files({YAML_CONFIG_FILE: """
yandex_smart_home:
  filter:
    include_domains:
      - script"""}):
        with patch(f'{COMPONENT_PATH}.async_setup', return_value=True) as mock_setup, patch(
                f'{COMPONENT_PATH}.async_setup_entry', return_value=True) as mock_setup_entry:
            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={'source': config_entries.SOURCE_USER}
            )
            assert result['type'] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
            mock_setup.assert_called_once()
            mock_setup_entry.assert_called_once()

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={'source': config_entries.SOURCE_USER}
        )
        assert result['type'] == 'abort'
        assert result['reason'] == 'single_instance_allowed'


async def test_step_user(hass):
    with patch_yaml_files({YAML_CONFIG_FILE: ''}):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={'source': config_entries.SOURCE_USER}
        )
        assert result['type'] == 'form'
        assert result['step_id'] == 'include_domains'
        assert result['errors'] is None

        with patch(f'{COMPONENT_PATH}.async_setup', return_value=True) as mock_setup, patch(
                f'{COMPONENT_PATH}.async_setup_entry', return_value=True) as mock_setup_entry:
            result2 = await hass.config_entries.flow.async_configure(result['flow_id'], {
                'include_domains': ['light']
            })
            await hass.async_block_till_done()

            assert result2['type'] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
            assert result2['data'] == {
                'filter': {
                    'exclude_entities': [],
                    'include_domains': ['light'],
                    'include_entities': []
                },
            }

            mock_setup.assert_called_once()
            mock_setup_entry.assert_called_once()


async def test_options_flow_with_yaml_filters(hass):
    config_entry = _mock_config_entry_with_options_populated()
    config_entry.add_to_hass(hass)

    with patch_yaml_files({YAML_CONFIG_FILE: """
    yandex_smart_home:
      filter:
        include_domains:
          - script"""}):
        result = await hass.config_entries.options.async_init(config_entry.entry_id)
        assert result['type'] == data_entry_flow.RESULT_TYPE_FORM
        assert result['step_id'] == 'include_domains_yaml'

        result2 = await hass.config_entries.options.async_configure(result['flow_id'], user_input={})
        assert result2['type'] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY


async def test_options_flow_filter_exclude(hass):
    config_entry = _mock_config_entry_with_options_populated()
    config_entry.add_to_hass(hass)

    hass.states.async_set('climate.old', 'off')
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
    config_entry = _mock_config_entry_with_options_populated()
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


async def test_options_flow_filter_exclude2(hass):
    config_entry = MockConfigEntry(
        domain=DOMAIN,
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
