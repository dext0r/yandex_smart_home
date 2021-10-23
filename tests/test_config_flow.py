from homeassistant import config_entries, data_entry_flow

from custom_components.yandex_smart_home.const import DOMAIN


async def test_step_user(hass):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={'source': config_entries.SOURCE_USER}
    )
    assert result['type'] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={'source': config_entries.SOURCE_USER}
    )
    assert result['type'] == 'abort'
    assert result['reason'] == 'single_instance_allowed'
