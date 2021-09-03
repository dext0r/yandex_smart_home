from homeassistant.config import YAML_CONFIG_FILE
from homeassistant.helpers.reload import async_integration_yaml_config

from custom_components.yandex_smart_home import DOMAIN, CONFIG_SCHEMA
from pytest_homeassistant_custom_component.common import mock_integration, MockModule, patch_yaml_files, load_fixture


async def test_bad_config(hass):
    files = {YAML_CONFIG_FILE: load_fixture('config/bad.yaml')}
    with patch_yaml_files(files):
        mock_integration(hass, MockModule(domain=DOMAIN, config_schema=CONFIG_SCHEMA), built_in=False)
        assert await async_integration_yaml_config(hass, DOMAIN) is None


async def test_valid_config(hass):
    files = {YAML_CONFIG_FILE: load_fixture('config/valid.yaml')}
    with patch_yaml_files(files):
        mock_integration(hass, MockModule(domain=DOMAIN, config_schema=CONFIG_SCHEMA), built_in=False)
        config = await async_integration_yaml_config(hass, DOMAIN)
        assert DOMAIN in config
        assert config[DOMAIN].keys() == {'notifier', 'settings', 'filter', 'entity_config'}
