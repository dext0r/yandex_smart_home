from homeassistant import config_entries, data_entry_flow
from homeassistant.config import YAML_CONFIG_FILE
from pytest_homeassistant_custom_component.common import patch_yaml_files

from custom_components.yandex_smart_home.const import DOMAIN


async def test_step_import(hass):
    with patch_yaml_files({YAML_CONFIG_FILE: 'yandex_smart_home:'}):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={'source': config_entries.SOURCE_IMPORT}
        )
        assert result['type'] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY


async def test_step_user(hass):
    with patch_yaml_files({YAML_CONFIG_FILE: ''}):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={'source': config_entries.SOURCE_USER}
        )
        assert result['type'] == 'abort'
        assert result['reason'] == 'missing_configuration'

    with patch_yaml_files({YAML_CONFIG_FILE: 'yandex_smart_home:'}):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={'source': config_entries.SOURCE_USER}
        )
        assert result['type'] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={'source': config_entries.SOURCE_USER}
        )
        assert result['type'] == 'abort'
        assert result['reason'] == 'single_instance_allowed'
