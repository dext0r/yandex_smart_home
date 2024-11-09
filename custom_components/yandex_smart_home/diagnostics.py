"""Diagnostics support for Yandex Smart Home."""

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry

from . import DOMAIN, YandexSmartHome
from .const import CONF_CLOUD_INSTANCE, CONF_SKILL
from .device import async_get_device_description, async_get_devices


async def async_get_config_entry_diagnostics(hass: HomeAssistant, config_entry: ConfigEntry) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    component: YandexSmartHome = hass.data[DOMAIN]
    entry_data = component.get_entry_data(config_entry)

    diag: dict[str, Any] = {
        "entry": async_redact_data(config_entry.as_dict(), [CONF_CLOUD_INSTANCE, CONF_SKILL]),
        "devices": {},
        "issues": [i.to_json() for i in issue_registry.async_get(hass).issues.values() if i.domain == DOMAIN],
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
