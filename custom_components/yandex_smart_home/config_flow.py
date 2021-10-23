from __future__ import annotations

import logging

from homeassistant import data_entry_flow
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.const import ATTR_FRIENDLY_NAME, CONF_DOMAINS, CONF_ENTITIES
from homeassistant.core import HomeAssistant, callback, split_entity_id
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entityfilter import CONF_EXCLUDE_ENTITIES, CONF_INCLUDE_DOMAINS, CONF_INCLUDE_ENTITIES
from homeassistant.helpers.reload import async_integration_yaml_config
from homeassistant.helpers.typing import ConfigType
import voluptuous as vol

from . import DOMAIN, const, is_config_filter_empty

_LOGGER = logging.getLogger(__name__)

CONF_INCLUDE_EXCLUDE_MODE = 'include_exclude_mode'

MODE_INCLUDE = 'include'
MODE_EXCLUDE = 'exclude'

SUPPORTED_DOMAINS = [
    'binary_sensor',
    'climate',
    'cover',
    'fan',
    'humidifier',
    'light',
    'lock',
    'media_player',
    'scene',
    'script',
    'sensor',
    'switch',
    'vacuum',
    'water_heater',
]

DEFAULT_DOMAINS = [
    'climate',
    'cover',
    'humidifier',
    'fan',
    'light',
    'lock',
    'media_player',
    'switch',
    'vacuum',
    'water_heater',
]

_EMPTY_ENTITY_FILTER = {
    CONF_INCLUDE_DOMAINS: [],
    CONF_INCLUDE_ENTITIES: [],
    CONF_EXCLUDE_ENTITIES: [],
}

INCLUDE_EXCLUDE_MODES = {
    MODE_INCLUDE: 'Включить',
    MODE_EXCLUDE: 'Исключить'
}


class ConfigFlowHandler(ConfigFlow, domain=DOMAIN):
    def __init__(self) -> None:
        self._data = {}

    async def async_step_user(self, user_input: ConfigType | None = None) -> data_entry_flow.FlowResult:
        if self._async_current_entries():
            return self.async_abort(reason='single_instance_allowed')

        return await self.async_step_include_domains()

    async def async_step_include_domains(self, user_input: ConfigType | None = None) -> data_entry_flow.FlowResult:
        yaml_config = await async_integration_yaml_config(self.hass, DOMAIN)
        if DOMAIN in yaml_config and not is_config_filter_empty(yaml_config[DOMAIN]):
            return await self.async_step_done()

        if user_input is not None:
            entity_filter = _EMPTY_ENTITY_FILTER.copy()
            entity_filter[CONF_INCLUDE_DOMAINS] = user_input[CONF_INCLUDE_DOMAINS]
            self._data[const.CONF_FILTER] = entity_filter
            return await self.async_step_done()

        return self.async_show_form(
            step_id='include_domains',
            data_schema=vol.Schema({
                vol.Required(
                    CONF_INCLUDE_DOMAINS, default=DEFAULT_DOMAINS
                ): cv.multi_select({v: v for v in SUPPORTED_DOMAINS}),
            }),
        )

    async def async_step_done(self) -> data_entry_flow.FlowResult:
        return self.async_create_entry(title='Yandex Smart Home', data=self._data)

    @staticmethod
    @callback
    def async_get_options_flow(entry: ConfigEntry) -> OptionsFlow:
        return OptionsFlowHandler(entry)


class OptionsFlowHandler(OptionsFlow):
    def __init__(self, entry: ConfigEntry):
        self._entry = entry
        self._options = dict(entry.options)

    async def async_step_init(self, _: ConfigType | None = None) -> data_entry_flow.FlowResult:
        return await self.async_step_include_domains()

    async def async_step_include_domains(self, user_input: ConfigType | None = None) -> data_entry_flow.FlowResult:
        yaml_config = await async_integration_yaml_config(self.hass, DOMAIN)
        if DOMAIN in yaml_config and not is_config_filter_empty(yaml_config[DOMAIN]):
            return await self.async_step_include_domains_yaml()

        if user_input is not None:
            self._options.update(user_input)
            return await self.async_step_include_exclude()

        entity_filter = self._options.get(const.CONF_FILTER, {})
        domains = entity_filter.get(CONF_INCLUDE_DOMAINS, [])
        include_entities = entity_filter.get(CONF_INCLUDE_ENTITIES)
        if include_entities:
            domains.extend(_domains_set_from_entities(include_entities))

        return self.async_show_form(
            step_id='include_domains',
            data_schema=vol.Schema({
                vol.Required(
                    CONF_DOMAINS, default=domains
                ): cv.multi_select({v: v for v in SUPPORTED_DOMAINS}),
            }),
        )

    async def async_step_include_domains_yaml(self, user_input: ConfigType | None = None) -> data_entry_flow.FlowResult:
        if user_input is not None:
            return await self.async_step_done()

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

            return await self.async_step_done()

        entity_filter = self._options.get(const.CONF_FILTER, {})
        all_supported_entities = _async_get_matching_entities(self.hass, domains=self._options[CONF_DOMAINS])
        entities = entity_filter.get(CONF_INCLUDE_ENTITIES, [])

        if entities:
            include_exclude_mode = MODE_INCLUDE
        else:
            include_exclude_mode = MODE_EXCLUDE
            entities = entity_filter.get(CONF_EXCLUDE_ENTITIES, [])

        return self.async_show_form(
            step_id='include_exclude',
            data_schema=vol.Schema({
                vol.Required(CONF_INCLUDE_EXCLUDE_MODE, default=include_exclude_mode): vol.In(INCLUDE_EXCLUDE_MODES),
                vol.Optional(CONF_ENTITIES, default=entities): cv.multi_select(all_supported_entities)
            })
        )

    async def async_step_done(self) -> data_entry_flow.FlowResult:
        for key in (CONF_DOMAINS, CONF_ENTITIES):
            if key in self._options:
                del self._options[key]

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
