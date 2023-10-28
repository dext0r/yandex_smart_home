from __future__ import annotations

import logging
from typing import Any

from aiohttp import ClientConnectorError, ClientResponseError
from homeassistant import data_entry_flow
from homeassistant.auth.const import GROUP_ID_READ_ONLY
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.const import CONF_ENTITIES
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowHandler
from homeassistant.helpers import selector
from homeassistant.helpers.entityfilter import CONF_INCLUDE_ENTITIES
from homeassistant.helpers.typing import ConfigType
import voluptuous as vol

from . import DOMAIN, FILTER_SCHEMA, YAML_CONFIG, const, get_config_entry_data_from_yaml_config
from .cloud import register_cloud_instance

_LOGGER = logging.getLogger(__name__)

CONNECTION_TYPES = {
    const.CONNECTION_TYPE_CLOUD: 'Через облако',
    const.CONNECTION_TYPE_DIRECT: 'Напрямую'
}


class BaseFlowHandler(FlowHandler):
    def __init__(self):
        self._data: dict[str, Any] = {}
        self._options: dict[str, Any] = {}

    def _populate_data_from_yaml_config(self):
        yaml_config = None
        if DOMAIN in self.hass.data:
            yaml_config = self.hass.data[DOMAIN][YAML_CONFIG]

        data, options = get_config_entry_data_from_yaml_config(self._data, self._options, yaml_config)
        self._data.update(data)
        self._options.update(options)


class ConfigFlowHandler(BaseFlowHandler, ConfigFlow, domain=DOMAIN):
    def __init__(self) -> None:
        super().__init__()

        self._yaml_config: ConfigType | None = None
        self._data: dict[str, Any] = {
            const.CONF_DEVICES_DISCOVERED: False
        }

    async def async_step_user(self, user_input: ConfigType | None = None) -> data_entry_flow.FlowResult:
        if self._async_current_entries():
            return self.async_abort(reason='single_instance_allowed')

        if DOMAIN in self.hass.data:
            yaml_config = self.hass.data[DOMAIN][YAML_CONFIG]

            if yaml_config and yaml_config.get(const.CONF_FILTER):
                return await self.async_step_filter_yaml()

        return await self.async_step_include_entities()

    async def async_step_filter_yaml(self, user_input: ConfigType | None = None) -> data_entry_flow.FlowResult:
        if user_input is not None:
            return await self.async_step_connection_type()

        return self.async_show_form(step_id='filter_yaml')

    async def async_step_include_entities(self, user_input: ConfigType | None = None) -> data_entry_flow.FlowResult:
        errors = {}
        if user_input is not None:
            if user_input[CONF_ENTITIES]:
                self._options[const.CONF_FILTER] = {
                    CONF_INCLUDE_ENTITIES: user_input[CONF_ENTITIES]
                }
                return await self.async_step_connection_type()
            else:
                errors['base'] = 'entities_not_selected'

        return self.async_show_form(
            step_id='include_entities',
            data_schema=vol.Schema({
                vol.Required(CONF_ENTITIES): selector.EntitySelector(
                    selector.EntitySelectorConfig(multiple=True)
                )
            }),
            errors=errors
        )

    async def async_step_connection_type(self, user_input: ConfigType | None = None) -> data_entry_flow.FlowResult:
        errors = {}
        if user_input is not None:
            self._data.update(user_input)

            entry_description = user_input[const.CONF_CONNECTION_TYPE]
            entry_description_placeholders = {}

            if user_input[const.CONF_CONNECTION_TYPE] == const.CONNECTION_TYPE_CLOUD:
                try:
                    instance = await register_cloud_instance(self.hass)
                    self._data[const.CONF_CLOUD_INSTANCE] = {
                        const.CONF_CLOUD_INSTANCE_ID: instance.id,
                        const.CONF_CLOUD_INSTANCE_PASSWORD: instance.password,
                        const.CONF_CLOUD_INSTANCE_CONNECTION_TOKEN: instance.connection_token
                    }
                except (ClientConnectorError, ClientResponseError):
                    errors['base'] = 'cannot_connect'
                    _LOGGER.exception('Failed to register instance in Yandex Smart Home cloud')
                else:
                    entry_description_placeholders.update(self._data[const.CONF_CLOUD_INSTANCE])

            if not errors:
                self._populate_data_from_yaml_config()

                return self.async_create_entry(
                    title=const.CONFIG_ENTRY_TITLE,
                    description=entry_description,
                    description_placeholders=entry_description_placeholders,
                    data=self._data,
                    options=self._options
                )

        return self.async_show_form(
            step_id='connection_type',
            data_schema=vol.Schema({
                vol.Required(const.CONF_CONNECTION_TYPE,
                             default=const.CONNECTION_TYPE_CLOUD): vol.In(CONNECTION_TYPES)
            }),
            errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(entry: ConfigEntry) -> OptionsFlow:
        return OptionsFlowHandler(entry)


class OptionsFlowHandler(BaseFlowHandler, OptionsFlow):
    def __init__(self, entry: ConfigEntry):
        super().__init__()

        self._entry = entry
        self._options = dict(entry.options)
        self._data = dict(entry.data)

    async def async_step_init(self, _: ConfigType | None = None) -> data_entry_flow.FlowResult:
        options = ['include_entities', 'connection_type']
        if self._data[const.CONF_CONNECTION_TYPE] == const.CONNECTION_TYPE_CLOUD:
            options += ['cloud_info', 'cloud_settings']

        return self.async_show_menu(step_id='init', menu_options=options)

    async def async_step_filter_yaml(self, user_input: ConfigType | None = None) -> data_entry_flow.FlowResult:
        if user_input is not None:
            return await self.async_step_init()

        return self.async_show_form(step_id='filter_yaml')

    async def async_step_include_entities(self, user_input: ConfigType | None = None) -> data_entry_flow.FlowResult:
        errors = {}
        entities = []
        yaml_config = self.hass.data[DOMAIN][YAML_CONFIG]

        if yaml_config and yaml_config.get(const.CONF_FILTER):
            return await self.async_step_filter_yaml()

        if const.CONF_FILTER in self._options:
            entities = set(self._options[const.CONF_FILTER].get(CONF_INCLUDE_ENTITIES, []))

            # migration from include_exclude filters
            entity_filter = FILTER_SCHEMA(self._options[const.CONF_FILTER])
            if not entity_filter.empty_filter:
                entities.update([
                    s.entity_id for s in self.hass.states.async_all() if entity_filter(s.entity_id)
                ])

        if user_input is not None:
            if user_input[CONF_ENTITIES]:
                self._options[const.CONF_FILTER] = {
                    CONF_INCLUDE_ENTITIES: user_input[CONF_ENTITIES]
                }

                return await self.async_step_done()
            else:
                errors['base'] = 'entities_not_selected'
                entities = []

        return self.async_show_form(
            step_id='include_entities',
            data_schema=vol.Schema({
                vol.Required(CONF_ENTITIES, default=sorted(entities)): selector.EntitySelector(
                    selector.EntitySelectorConfig(multiple=True)
                )
            }),
            errors=errors
        )

    async def async_step_connection_type(self, user_input: ConfigType | None = None) -> data_entry_flow.FlowResult:
        errors = {}
        if user_input is not None:
            self._data.update(user_input)

            if user_input[const.CONF_CONNECTION_TYPE] == const.CONNECTION_TYPE_CLOUD and \
                    const.CONF_CLOUD_INSTANCE not in self._data:
                try:
                    instance = await register_cloud_instance(self.hass)
                    self._data[const.CONF_CLOUD_INSTANCE] = {
                        const.CONF_CLOUD_INSTANCE_ID: instance.id,
                        const.CONF_CLOUD_INSTANCE_PASSWORD: instance.password,
                        const.CONF_CLOUD_INSTANCE_CONNECTION_TOKEN: instance.connection_token
                    }
                except (ClientConnectorError, ClientResponseError):
                    errors['base'] = 'cannot_connect'
                    _LOGGER.exception('Failed to register instance in Yandex Smart Home cloud')

            if not errors:
                self._populate_data_from_yaml_config()
                self.hass.config_entries.async_update_entry(self._entry, data=self._data, options=self._options)
                return self.async_create_entry(title='', data=self._options)

        return self.async_show_form(
            step_id='connection_type',
            data_schema=vol.Schema({
                vol.Required(const.CONF_CONNECTION_TYPE,
                             default=self._data[const.CONF_CONNECTION_TYPE]): vol.In(CONNECTION_TYPES)
            }),
            errors=errors
        )

    async def async_step_cloud_settings(self, user_input: ConfigType | None = None) -> data_entry_flow.FlowResult:
        if user_input is not None:
            self._options.update(user_input)
            return await self.async_step_done()

        return self.async_show_form(step_id='cloud_settings', data_schema=vol.Schema({
            vol.Required(const.CONF_USER_ID, default=self._options.get(const.CONF_USER_ID)): vol.In(
                await _async_get_users(self.hass)
            )
        }))

    async def async_step_cloud_info(self, user_input: ConfigType | None = None) -> data_entry_flow.FlowResult:
        if user_input is not None:
            return await self.async_step_init()

        instance = self._data[const.CONF_CLOUD_INSTANCE]
        return self.async_show_form(step_id='cloud_info', description_placeholders={
            const.CONF_CLOUD_INSTANCE_ID: instance[const.CONF_CLOUD_INSTANCE_ID],
            const.CONF_CLOUD_INSTANCE_PASSWORD: instance[const.CONF_CLOUD_INSTANCE_PASSWORD]
        })

    async def async_step_done(self) -> data_entry_flow.FlowResult:
        return self.async_create_entry(title='', data=self._options)


async def _async_get_users(hass: HomeAssistant) -> dict[str, str]:
    rv = {}
    for user in await hass.auth.async_get_users():
        if any(gr.id == GROUP_ID_READ_ONLY for gr in user.groups):
            continue

        rv[user.id] = user.name

    return rv
