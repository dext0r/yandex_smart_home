from __future__ import annotations

import asyncio
import logging
from typing import Any

from aiohttp import ClientConnectorError, ClientResponseError
from homeassistant import data_entry_flow
from homeassistant.auth.const import GROUP_ID_READ_ONLY
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.const import ATTR_FRIENDLY_NAME, CONF_DOMAINS, CONF_ENTITIES
from homeassistant.core import HomeAssistant, callback, split_entity_id
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entityfilter import CONF_EXCLUDE_ENTITIES, CONF_INCLUDE_DOMAINS, CONF_INCLUDE_ENTITIES
from homeassistant.helpers.typing import ConfigType
from homeassistant.loader import async_get_integration
import voluptuous as vol

from . import DOMAIN, YAML_CONFIG, _get_config_entry_data_from_yaml, const
from .cloud import register_cloud_instance

_LOGGER = logging.getLogger(__name__)

CONF_INCLUDE_EXCLUDE_MODE = 'include_exclude_mode'

MODE_INCLUDE = 'include'
MODE_EXCLUDE = 'exclude'

_EMPTY_ENTITY_FILTER = {
    CONF_INCLUDE_DOMAINS: [],
    CONF_INCLUDE_ENTITIES: [],
    CONF_EXCLUDE_ENTITIES: [],
}

CONNECTION_TYPES = {
    const.CONNECTION_TYPE_DIRECT: 'Напрямую',
    const.CONNECTION_TYPE_CLOUD: 'Через облако (бета-тест)'
}

INCLUDE_EXCLUDE_MODES = {
    MODE_INCLUDE: 'Включить',
    MODE_EXCLUDE: 'Исключить'
}


class ConfigFlowHandler(ConfigFlow, domain=DOMAIN):
    def __init__(self) -> None:
        self._yaml_config: ConfigType | None = None
        self._data: dict[str, Any] = {
            const.CONF_DEVICES_DISCOVERED: False
        }

    async def async_step_user(self, user_input: ConfigType | None = None) -> data_entry_flow.FlowResult:
        if self._async_current_entries():
            return self.async_abort(reason='single_instance_allowed')

        if DOMAIN in self.hass.data:
            self._yaml_config = self.hass.data[DOMAIN][YAML_CONFIG]
            self._data.update(_get_config_entry_data_from_yaml(self._data, self._yaml_config))

        return await self.async_step_connection_type()

    async def async_step_connection_type(self, user_input: ConfigType | None = None) -> data_entry_flow.FlowResult:
        errors = {}
        if user_input is not None:
            self._data.update(user_input)
            if user_input[const.CONF_CONNECTION_TYPE] == const.CONNECTION_TYPE_CLOUD:
                try:
                    return await self.async_step_cloud()
                except (ClientConnectorError, ClientResponseError):
                    errors['base'] = 'cannot_connect'
                    _LOGGER.exception('Failed to register instance in Yandex Smart Home cloud')
            else:
                return self.async_create_entry(title=const.CONFIG_ENTRY_TITLE, data=self._data)

        return self.async_show_form(
            step_id='connection_type',
            data_schema=vol.Schema({
                vol.Required(const.CONF_CONNECTION_TYPE,
                             default=const.CONNECTION_TYPE_CLOUD): vol.In(CONNECTION_TYPES)
            }),
            errors=errors
        )

    async def async_step_cloud(self) -> data_entry_flow.FlowResult:
        instance = await register_cloud_instance(self.hass)
        self._data[const.CONF_CLOUD_INSTANCE] = {
            const.CONF_CLOUD_INSTANCE_ID: instance.id,
            const.CONF_CLOUD_INSTANCE_PASSWORD: instance.password,
            const.CONF_CLOUD_INSTANCE_CONNECTION_TOKEN: instance.connection_token
        }

        return self.async_create_entry(
            title=const.CONFIG_ENTRY_TITLE,
            data=self._data,
            description='cloud',
            description_placeholders={
                const.CONF_CLOUD_INSTANCE_ID: instance.id,
                const.CONF_CLOUD_INSTANCE_PASSWORD: instance.password
            }
        )

    @staticmethod
    @callback
    def async_get_options_flow(entry: ConfigEntry) -> OptionsFlow:
        return OptionsFlowHandler(entry)


class OptionsFlowHandler(OptionsFlow):
    def __init__(self, entry: ConfigEntry):
        self._entry = entry
        self._options = dict(entry.options)
        self._data = dict(entry.data)

    async def async_step_init(self, _: ConfigType | None = None) -> data_entry_flow.FlowResult:
        return await self.async_step_include_domains()

    async def async_step_include_domains(self, user_input: ConfigType | None = None) -> data_entry_flow.FlowResult:
        errors = {}
        yaml_config = self.hass.data[DOMAIN][YAML_CONFIG]

        if yaml_config and yaml_config.get(const.CONF_FILTER):
            return await self.async_step_include_domains_yaml()

        if user_input is not None:
            domains = user_input[CONF_DOMAINS]
            if domains:
                self._options.update(user_input)
                return await self.async_step_include_exclude()
            else:
                errors['base'] = 'domains_not_selected'
        else:
            entity_filter = self._options.get(const.CONF_FILTER, _EMPTY_ENTITY_FILTER)
            domains = set(entity_filter[CONF_INCLUDE_DOMAINS])
            include_entities = entity_filter[CONF_INCLUDE_ENTITIES]
            if include_entities:
                domains.update(_domains_set_from_entities(include_entities))

        name_to_type_map = await _async_name_to_type_map(self.hass)

        return self.async_show_form(
            step_id='include_domains',
            data_schema=vol.Schema({
                vol.Required(CONF_DOMAINS, default=sorted(domains)): cv.multi_select(name_to_type_map)
            }),
            errors=errors
        )

    async def async_step_include_domains_yaml(self, user_input: ConfigType | None = None) -> data_entry_flow.FlowResult:
        if user_input is not None:
            return await self.async_step_cloud_settings()

        return self.async_show_form(step_id='include_domains_yaml')

    async def async_step_include_exclude(self, user_input: ConfigType | None = None) -> data_entry_flow.FlowResult:
        """Choose entities to include or exclude from the domain."""
        if user_input is not None:
            entity_filter = _EMPTY_ENTITY_FILTER.copy()
            entities = user_input[CONF_ENTITIES]

            if user_input[CONF_INCLUDE_EXCLUDE_MODE] == MODE_INCLUDE:
                entity_filter[CONF_INCLUDE_ENTITIES] = entities

                # Include all of the domain if there are no entities
                # explicitly included as the user selected the domain
                domains_with_entities_selected = _domains_set_from_entities(entities)
                entity_filter[CONF_INCLUDE_DOMAINS] = [
                    domain
                    for domain in self._options[CONF_DOMAINS]
                    if domain not in domains_with_entities_selected
                ]
            else:
                entity_filter[CONF_INCLUDE_DOMAINS] = self._options[CONF_DOMAINS]
                entity_filter[CONF_EXCLUDE_ENTITIES] = entities

            self._options[const.CONF_FILTER] = entity_filter

            for key in (CONF_DOMAINS, CONF_ENTITIES):
                if key in self._options:
                    del self._options[key]

            return await self.async_step_cloud_settings()

        entity_filter = self._options.get(const.CONF_FILTER, _EMPTY_ENTITY_FILTER)
        all_supported_entities = _async_get_matching_entities(self.hass, domains=self._options[CONF_DOMAINS])
        entities = entity_filter[CONF_INCLUDE_ENTITIES]
        include_exclude_mode = MODE_INCLUDE

        if not entities:
            include_exclude_mode = MODE_EXCLUDE
            entities = entity_filter.get(CONF_EXCLUDE_ENTITIES, [])

        entities = [
            entity_id
            for entity_id in entities
            if entity_id in all_supported_entities
        ]

        return self.async_show_form(
            step_id='include_exclude',
            data_schema=vol.Schema({
                vol.Required(CONF_INCLUDE_EXCLUDE_MODE, default=include_exclude_mode): vol.In(INCLUDE_EXCLUDE_MODES),
                vol.Optional(CONF_ENTITIES, default=sorted(entities)): cv.multi_select(all_supported_entities)
            })
        )

    async def async_step_cloud_settings(self, user_input: ConfigType | None = None) -> data_entry_flow.FlowResult:
        if self._data[const.CONF_CONNECTION_TYPE] == const.CONNECTION_TYPE_DIRECT:
            return await self.async_step_done()

        if user_input is not None:
            self._options.update(user_input)
            return await self.async_step_cloud_info()

        return self.async_show_form(step_id='cloud_settings', data_schema=vol.Schema({
            vol.Required(const.CONF_USER_ID, default=self._options.get(const.CONF_USER_ID)): vol.In(
                await _async_get_users(self.hass)
            )
        }))

    async def async_step_cloud_info(self, user_input: ConfigType | None = None) -> data_entry_flow.FlowResult:
        if user_input is not None:
            return await self.async_step_done()

        instance = self._data[const.CONF_CLOUD_INSTANCE]
        return self.async_show_form(step_id='cloud_info', description_placeholders={
            const.CONF_CLOUD_INSTANCE_ID: instance[const.CONF_CLOUD_INSTANCE_ID],
            const.CONF_CLOUD_INSTANCE_PASSWORD: instance[const.CONF_CLOUD_INSTANCE_PASSWORD]
        })

    async def async_step_done(self) -> data_entry_flow.FlowResult:
        return self.async_create_entry(title='', data=self._options)


def _domains_set_from_entities(entity_ids: list[str]) -> set[str]:
    """Build a set of domains for the given entity ids."""
    return {split_entity_id(entity_id)[0] for entity_id in entity_ids}


def _async_get_matching_entities(hass: HomeAssistant, domains: list[str] | None = None):
    """Fetch all entities or entities in the given domains."""
    return {
        state.entity_id: f'{state.attributes.get(ATTR_FRIENDLY_NAME, state.entity_id)} ({state.entity_id})'
        for state in sorted(
            hass.states.async_all(domains and set(domains)),
            key=lambda item: item.entity_id,
        )
    }


async def _async_get_users(hass: HomeAssistant) -> dict[str, str]:
    rv = {}
    for user in await hass.auth.async_get_users():
        if any(gr.id == GROUP_ID_READ_ONLY for gr in user.groups):
            continue

        rv[user.id] = user.name

    return rv


async def _async_name_to_type_map(hass: HomeAssistant) -> dict[str, str]:
    """Create a mapping of types of devices/entities Yandex Smart Home can support."""
    supported_domains = sorted(const.DOMAIN_TO_YANDEX_TYPES)
    integrations = await asyncio.gather(
        *[async_get_integration(hass, domain) for domain in supported_domains],
        return_exceptions=True,
    )
    name_to_type_map = {
        domain: domain
        if isinstance(integrations[idx], Exception)
        else integrations[idx].name
        for idx, domain in enumerate(supported_domains)
    }

    return name_to_type_map
