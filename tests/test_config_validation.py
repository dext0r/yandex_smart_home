from homeassistant.config import YAML_CONFIG_FILE
from homeassistant.helpers.reload import async_integration_yaml_config
from pytest_homeassistant_custom_component.common import patch_yaml_files

from custom_components.yandex_smart_home import DOMAIN


async def test_invalid_property_type(hass, caplog):
    files = {
        YAML_CONFIG_FILE: """
yandex_smart_home:
  entity_config:
    sensor.test:
      properties:
        - type: invalid
          entity: sensor.test
"""
    }
    with patch_yaml_files(files):
        assert await async_integration_yaml_config(hass, DOMAIN) is None

    assert "Property type 'invalid' is not supported. See valid types at" in caplog.messages[-1]


async def test_invalid_mode(hass, caplog):
    files = {
        YAML_CONFIG_FILE: """
yandex_smart_home:
  entity_config:
    sensor.test:
      modes:
        fan_speed:
          invalid: ['invalid']
"""
    }
    with patch_yaml_files(files):
        assert await async_integration_yaml_config(hass, DOMAIN) is None
    assert "Mode 'invalid' is not supported. See valid modes at" in caplog.messages[-2]


async def test_invalid_mode_instance(hass, caplog):
    files = {
        YAML_CONFIG_FILE: """
yandex_smart_home:
  entity_config:
    sensor.test:
      modes:
        invalid:
"""
    }
    with patch_yaml_files(files):
        assert await async_integration_yaml_config(hass, DOMAIN) is None
    assert "Mode instance 'invalid' is not supported. See valid modes at" in caplog.messages[-2]


async def test_invalid_toggle_instance(hass, caplog):
    files = {
        YAML_CONFIG_FILE: """
yandex_smart_home:
  entity_config:
    sensor.test:
      custom_toggles:
        invalid:
"""
    }
    with patch_yaml_files(files):
        assert await async_integration_yaml_config(hass, DOMAIN) is None
    assert "Toggle instance 'invalid' is not supported. See valid values at" in caplog.messages[-2]


async def test_invalid_range_instance(hass, caplog):
    files = {
        YAML_CONFIG_FILE: """
yandex_smart_home:
  entity_config:
    sensor.test:
      custom_ranges:
        invalid:
"""
    }
    with patch_yaml_files(files):
        assert await async_integration_yaml_config(hass, DOMAIN) is None
    assert "Range instance 'invalid' is not supported. See valid values at" in caplog.messages[-2]


async def test_invalid_entity_feature(hass, caplog):
    files = {
        YAML_CONFIG_FILE: """
yandex_smart_home:
  entity_config:
    media_player.test:
      features:
        - invalid
"""
    }
    with patch_yaml_files(files):
        assert await async_integration_yaml_config(hass, DOMAIN) is None
    assert "Feature 'invalid' is not supported" in caplog.messages[-1]


async def test_invalid_device_type(hass, caplog):
    files = {
        YAML_CONFIG_FILE: """
yandex_smart_home:
  entity_config:
    media_player.test:
      type: unsupported
"""
    }
    with patch_yaml_files(files):
        assert await async_integration_yaml_config(hass, DOMAIN) is None
    assert "Device type 'unsupported' is not supported" in caplog.messages[-1]


async def test_invalid_pressure_unit(hass):
    files = {
        YAML_CONFIG_FILE: """
yandex_smart_home:
  settings:
    pressure_unit: invalid
"""
    }
    with patch_yaml_files(files):
        assert await async_integration_yaml_config(hass, DOMAIN) is None


async def test_invalid_color_name(hass, caplog):
    files = {
        YAML_CONFIG_FILE: """
yandex_smart_home:
  color_profile:
    test:
      invalid: [1, 2, 3]
"""
    }
    with patch_yaml_files(files):
        assert await async_integration_yaml_config(hass, DOMAIN) is None
    assert "Color name 'invalid' is not supported. See valid values at" in caplog.messages[-2]


async def test_color_value(hass):
    files = {
        YAML_CONFIG_FILE: """
yandex_smart_home:
  color_profile:
    test:
      red: [255, 255, 0]
"""
    }
    with patch_yaml_files(files):
        config = await async_integration_yaml_config(hass, DOMAIN)
        assert config[DOMAIN]["color_profile"]["test"]["red"] == 16776960

    files = {
        YAML_CONFIG_FILE: """
yandex_smart_home:
  color_profile:
    test:
      red: 123456
"""
    }
    with patch_yaml_files(files):
        config = await async_integration_yaml_config(hass, DOMAIN)
        assert config[DOMAIN]["color_profile"]["test"]["red"] == 123456

    files = {
        YAML_CONFIG_FILE: """
yandex_smart_home:
  color_profile:
    test:
      red: [1, 2]
"""
    }
    with patch_yaml_files(files):
        assert await async_integration_yaml_config(hass, DOMAIN) is None


async def test_property_type_button(hass, caplog):
    files = {
        YAML_CONFIG_FILE: """
yandex_smart_home:
  entity_config:
    media_player.test:
      properties:
        - type: button
          attribute: bla
"""
    }
    with patch_yaml_files(files):
        await async_integration_yaml_config(hass, DOMAIN)
        assert "Property type 'button' is not supported" in caplog.messages[-1]
