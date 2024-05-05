"""Diagnostics support for Yandex Smart Home."""

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.yandex_smart_home.device import async_get_device_description, async_get_devices

from . import DOMAIN, YandexSmartHome, const


async def async_get_config_entry_diagnostics(hass: HomeAssistant, config_entry: ConfigEntry) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    component: YandexSmartHome = hass.data[DOMAIN]
    entry_data = component.get_entry_data(config_entry)

    diag = {
        "entry": async_redact_data(config_entry.as_dict(), [const.CONF_CLOUD_INSTANCE]),
        "devices": {},
    }
    diag.update(component.get_diagnostics())

    for device in await async_get_devices(hass, entry_data):
        diag["devices"][device.id] = {
            "capabilities": [c.__repr__() for c in device.get_capabilities()],
            "properties": [p.__repr__() for p in device.get_properties()],
            "description": await async_get_device_description(hass, device),
            "state": device.query(),
        }

    return async_redact_data(diag, [])
