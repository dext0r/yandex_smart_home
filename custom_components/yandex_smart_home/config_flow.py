"""Config flow for the Yandex Smart Home integration."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Mapping

from aiohttp import ClientConnectorError, ClientResponseError
from homeassistant.auth.const import GROUP_ID_READ_ONLY
from homeassistant.config_entries import ConfigFlow, OptionsFlow
from homeassistant.const import CONF_ENTITIES
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector
from homeassistant.helpers.entityfilter import CONF_INCLUDE_ENTITIES
import voluptuous as vol

from . import DOMAIN, FILTER_SCHEMA, const
from .cloud import register_cloud_instance
from .const import ConnectionType

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers import ConfigType

    from . import YandexSmartHome

_LOGGER = logging.getLogger(__name__)

CONNECTION_TYPES = {ConnectionType.CLOUD: "Через облако", ConnectionType.DIRECT: "Напрямую"}
DEFAULT_CONFIG_ENTRY_TITLE = "Yandex Smart Home"


class ConfigFlowHandler(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Yandex Smart Home."""

    VERSION = 3

    def __init__(self) -> None:
        """Initialize a config flow handler."""
        super().__init__()

        self._data: ConfigType = {const.CONF_DEVICES_DISCOVERED: False}
        self._options: ConfigType = {}

    async def async_step_user(self, user_input: ConfigType | None = None) -> FlowResult:
        """Handle a flow initialized by the user."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if DOMAIN in self.hass.data:
            component: YandexSmartHome = self.hass.data[DOMAIN]
            if component.yaml_config_has_filter():
                return await self.async_step_filter_yaml()

        return await self.async_step_include_entities()

    async def async_step_filter_yaml(self, user_input: ConfigType | None = None) -> FlowResult:
        """Show warning about filter was configured in yaml."""
        if user_input is not None:
            return await self.async_step_connection_type()

        return self.async_show_form(step_id="filter_yaml")

    async def async_step_include_entities(self, user_input: ConfigType | None = None) -> FlowResult:
        """Choose entities that should be exposed."""
        errors = {}
        if user_input is not None:
            if user_input[CONF_ENTITIES]:
                self._options[const.CONF_FILTER] = {CONF_INCLUDE_ENTITIES: user_input[CONF_ENTITIES]}
                return await self.async_step_connection_type()
            else:
                errors["base"] = "entities_not_selected"

        return self.async_show_form(
            step_id="include_entities",
            data_schema=vol.Schema(
                {vol.Required(CONF_ENTITIES): selector.EntitySelector(selector.EntitySelectorConfig(multiple=True))}
            ),
            errors=errors,
        )

    async def async_step_connection_type(self, user_input: ConfigType | None = None) -> FlowResult:
        """Choose connection type."""
        errors = {}
        if user_input is not None:
            self._data.update(user_input)

            entry_description = user_input[const.CONF_CONNECTION_TYPE]
            entry_description_placeholders = {}

            if user_input[const.CONF_CONNECTION_TYPE] == ConnectionType.CLOUD:
                try:
                    instance = await register_cloud_instance(self.hass)
                    self._data[const.CONF_CLOUD_INSTANCE] = {
                        const.CONF_CLOUD_INSTANCE_ID: instance.id,
                        const.CONF_CLOUD_INSTANCE_PASSWORD: instance.password,
                        const.CONF_CLOUD_INSTANCE_CONNECTION_TOKEN: instance.connection_token,
                    }
                except (ClientConnectorError, ClientResponseError):
                    errors["base"] = "cannot_connect"
                    _LOGGER.exception("Failed to register instance in Yandex Smart Home cloud")
                else:
                    entry_description_placeholders.update(self._data[const.CONF_CLOUD_INSTANCE])

            if not errors:
                return self.async_create_entry(
                    title=config_entry_title(self._data),
                    description=entry_description,
                    description_placeholders=entry_description_placeholders,
                    data=self._data,
                    options=self._options,
                )

        return self.async_show_form(
            step_id="connection_type",
            data_schema=vol.Schema(
                {vol.Required(const.CONF_CONNECTION_TYPE, default=ConnectionType.CLOUD): vol.In(CONNECTION_TYPES)}
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(entry: ConfigEntry) -> OptionsFlow:
        """Get the options flow for this handler."""
        return OptionsFlowHandler(entry)


class OptionsFlowHandler(OptionsFlow):
    """Handle a options flow for Yandex Smart Home."""

    def __init__(self, entry: ConfigEntry):
        """Initialize an options flow handler."""

        super().__init__()

        self._entry = entry
        self._data: ConfigType = entry.data.copy()
        self._options: ConfigType = entry.options.copy()

    async def async_step_init(self, _: ConfigType | None = None) -> FlowResult:
        """Show menu."""
        options = ["include_entities", "connection_type"]
        if self._data[const.CONF_CONNECTION_TYPE] == ConnectionType.CLOUD:
            options += ["cloud_info", "cloud_settings"]

        return self.async_show_menu(step_id="init", menu_options=options)

    async def async_step_filter_yaml(self, user_input: ConfigType | None = None) -> FlowResult:
        """Show warning about filter was configured in yaml."""
        if user_input is not None:
            return await self.async_step_init()

        return self.async_show_form(step_id="filter_yaml")

    async def async_step_include_entities(self, user_input: ConfigType | None = None) -> FlowResult:
        """Choose entities that should be exposed."""

        errors = {}
        entities: set[str] = set()
        component: YandexSmartHome = self.hass.data[DOMAIN]
        if component.yaml_config_has_filter():
            return await self.async_step_filter_yaml()

        if const.CONF_FILTER in self._options:
            entities = set(self._options[const.CONF_FILTER].get(CONF_INCLUDE_ENTITIES, []))

            # migration from include_exclude filters
            entity_filter = FILTER_SCHEMA(self._options[const.CONF_FILTER])
            if not entity_filter.empty_filter:
                entities.update([s.entity_id for s in self.hass.states.async_all() if entity_filter(s.entity_id)])

        if user_input is not None:
            if user_input[CONF_ENTITIES]:
                self._options[const.CONF_FILTER] = {CONF_INCLUDE_ENTITIES: user_input[CONF_ENTITIES]}

                return await self.async_step_done()
            else:
                errors["base"] = "entities_not_selected"
                entities.clear()

        return self.async_show_form(
            step_id="include_entities",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ENTITIES, default=sorted(entities)): selector.EntitySelector(
                        selector.EntitySelectorConfig(multiple=True)
                    )
                }
            ),
            errors=errors,
        )

    async def async_step_connection_type(self, user_input: ConfigType | None = None) -> FlowResult:
        """Choose connection type."""

        errors = {}
        if user_input is not None:
            self._data.update(user_input)

            if (
                user_input[const.CONF_CONNECTION_TYPE] == ConnectionType.CLOUD
                and const.CONF_CLOUD_INSTANCE not in self._data
            ):
                try:
                    instance = await register_cloud_instance(self.hass)
                    self._data[const.CONF_CLOUD_INSTANCE] = {
                        const.CONF_CLOUD_INSTANCE_ID: instance.id,
                        const.CONF_CLOUD_INSTANCE_PASSWORD: instance.password,
                        const.CONF_CLOUD_INSTANCE_CONNECTION_TOKEN: instance.connection_token,
                    }
                except (ClientConnectorError, ClientResponseError):
                    errors["base"] = "cannot_connect"
                    _LOGGER.exception("Failed to register instance in Yandex Smart Home cloud")

            if not errors:
                self.hass.config_entries.async_update_entry(
                    self._entry, title=config_entry_title(self._data), data=self._data, options=self._options
                )
                return self.async_create_entry(data=self._options)

        return self.async_show_form(
            step_id="connection_type",
            data_schema=vol.Schema(
                {
                    vol.Required(const.CONF_CONNECTION_TYPE, default=self._data[const.CONF_CONNECTION_TYPE]): vol.In(
                        CONNECTION_TYPES
                    )
                }
            ),
            errors=errors,
        )

    async def async_step_cloud_settings(self, user_input: ConfigType | None = None) -> FlowResult:
        """Choose additional cloud options."""
        if user_input is not None:
            self._options.update(user_input)
            return await self.async_step_done()

        return self.async_show_form(
            step_id="cloud_settings",
            data_schema=vol.Schema(
                {
                    vol.Required(const.CONF_USER_ID, default=self._options.get(const.CONF_USER_ID)): vol.In(
                        await _async_get_users(self.hass)
                    )
                }
            ),
        )

    async def async_step_cloud_info(self, user_input: ConfigType | None = None) -> FlowResult:
        """Show cloud connection credential."""
        if user_input is not None:
            return await self.async_step_init()

        instance = self._data[const.CONF_CLOUD_INSTANCE]
        return self.async_show_form(
            step_id="cloud_info",
            description_placeholders={
                const.CONF_CLOUD_INSTANCE_ID: instance[const.CONF_CLOUD_INSTANCE_ID],
                const.CONF_CLOUD_INSTANCE_PASSWORD: instance[const.CONF_CLOUD_INSTANCE_PASSWORD],
            },
        )

    async def async_step_done(self) -> FlowResult:
        """Finish the flow."""
        return self.async_create_entry(data=self._options)


async def _async_get_users(hass: HomeAssistant) -> dict[str, str]:
    """Return users with admin privileges."""
    users = {}
    for user in await hass.auth.async_get_users():
        if any(gr.id == GROUP_ID_READ_ONLY for gr in user.groups):
            continue

        users[user.id] = user.name or user.id

    return users


def config_entry_title(data: Mapping[str, Any]) -> str:
    """Return config entry title."""
    match data.get(const.CONF_CONNECTION_TYPE):
        case ConnectionType.CLOUD:
            instance_id = data[const.CONF_CLOUD_INSTANCE][const.CONF_CLOUD_INSTANCE_ID]
            return f"Yaha Cloud ({instance_id[:8]})"
        case ConnectionType.DIRECT:
            return "YSH: Direct"  # ready for Marusia support

    return DEFAULT_CONFIG_ENTRY_TITLE
