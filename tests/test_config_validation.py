from homeassistant.config import YAML_CONFIG_FILE
from homeassistant.helpers.reload import async_integration_yaml_config
import pytest
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

    assert (
        "Property type 'invalid' is not supported, see valid types at "
        "https://docs.yaha-cloud.ru/master/devices/sensor/event/#type and "
        "https://docs.yaha-cloud.ru/master/devices/sensor/float/#type" in caplog.messages[-1]
    )


async def test_invalid_event_property_type(hass, caplog):
    files = {
        YAML_CONFIG_FILE: """
yandex_smart_home:
  entity_config:
    sensor.test:
      properties:
        - type: event.invalid
          entity: sensor.test
"""
    }
    with patch_yaml_files(files):
        assert await async_integration_yaml_config(hass, DOMAIN) is None

    assert (
        "Event property type 'invalid' is not supported, see valid event types at "
        "https://docs.yaha-cloud.ru/master/devices/sensor/event/#type"
    ) in caplog.messages[-1]


async def test_invalid_float_property_type(hass, caplog):
    files = {
        YAML_CONFIG_FILE: """
yandex_smart_home:
  entity_config:
    sensor.test:
      properties:
        - type: float.invalid
          entity: sensor.test
"""
    }
    with patch_yaml_files(files):
        assert await async_integration_yaml_config(hass, DOMAIN) is None

    assert (
        "Float property type 'invalid' is not supported, see valid float types at "
        "https://docs.yaha-cloud.ru/master/devices/sensor/float/#type"
    ) in caplog.messages[-1]


async def test_invalid_property(hass, caplog):
    files = {
        YAML_CONFIG_FILE: """
yandex_smart_home:
  entity_config:
    media_player.test:
      properties:
        - type: temperature
          entity: sensor.x   
          value_template: foo
"""
    }
    with patch_yaml_files(files):
        assert await async_integration_yaml_config(hass, DOMAIN) is None
    assert "entity/attribute and value_template are mutually exclusive" in caplog.messages[-1]

    files = {
        YAML_CONFIG_FILE: """
yandex_smart_home:
  entity_config:
    media_player.test:
      properties:
        - type: temperature
          attribute: bar  
          value_template: foo
"""
    }
    with patch_yaml_files(files):
        caplog.clear()
        assert await async_integration_yaml_config(hass, DOMAIN) is None
    assert "entity/attribute and value_template are mutually exclusive" in caplog.messages[-1]

    files = {
        YAML_CONFIG_FILE: """
yandex_smart_home:
  entity_config:
    media_player.test:
      properties:
        - type: temperature
          entity: sensor.x   
          attribute: bar
          value_template: foo
"""
    }
    with patch_yaml_files(files):
        caplog.clear()
        assert await async_integration_yaml_config(hass, DOMAIN) is None
    assert "entity/attribute and value_template are mutually exclusive" in caplog.messages[-1]


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
    assert (
        "Mode 'invalid' is not supported, see valid modes at "
        "https://yandex.ru/dev/dialogs/smart-home/doc/concepts/mode-instance-modes.html and "
        "https://docs.yaha-cloud.ru/master/devices/light/#scene-list" in caplog.messages[-2]
    )


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
    assert (
        "Mode instance 'invalid' is not supported, see valid modes at "
        "https://yandex.ru/dev/dialogs/smart-home/doc/concepts/mode-instance.html"
    ) in caplog.messages[-2]


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
    assert (
        "Toggle instance 'invalid' is not supported, see valid values at "
        "https://yandex.ru/dev/dialogs/smart-home/doc/concepts/toggle-instance.html"
    ) in caplog.messages[-2]


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
    assert (
        "Range instance 'invalid' is not supported, see valid values at "
        "https://yandex.ru/dev/dialogs/smart-home/doc/concepts/range-instance.html"
    ) in caplog.messages[-2]


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
    assert "Feature invalid is not supported" in caplog.messages[-1]


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
    assert (
        "Color name 'invalid' is not supported, see valid values at "
        "https://docs.yaha-cloud.ru/master/devices/light/#color-profile-config" in caplog.messages[-2]
    )


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


@pytest.mark.parametrize(
    "key,instance",
    [
        ("custom_ranges", "volume"),
        ("custom_toggles", "mute"),
        ("custom_modes", "swing"),
    ],
)
async def test_invalid_custom_capability(hass, key, instance, caplog):
    files = {
        YAML_CONFIG_FILE: f"""
yandex_smart_home:
  entity_config:
    media_player.test:
      {key}:
        {instance}:
          state_entity_id: sensor.x   
          state_template: foo
"""
    }
    with patch_yaml_files(files):
        assert await async_integration_yaml_config(hass, DOMAIN) is None
    assert "state_entity_id/state_attribute and state_template are mutually exclusive" in caplog.messages[-1]

    files = {
        YAML_CONFIG_FILE: f"""
yandex_smart_home:
  entity_config:
    media_player.test:
      {key}:
        {instance}:
          state_attribute: bar  
          state_template: foo
"""
    }
    with patch_yaml_files(files):
        caplog.clear()
        assert await async_integration_yaml_config(hass, DOMAIN) is None
    assert "state_entity_id/state_attribute and state_template are mutually exclusive" in caplog.messages[-1]

    files = {
        YAML_CONFIG_FILE: f"""
yandex_smart_home:
  entity_config:
    media_player.test:
      {key}:
        {instance}:
          state_entity_id: sensor.x   
          state_attribute: bar
          state_template: foo
"""
    }
    with patch_yaml_files(files):
        caplog.clear()
        assert await async_integration_yaml_config(hass, DOMAIN) is None
    assert "state_entity_id/state_attribute and state_template are mutually exclusive" in caplog.messages[-1]
