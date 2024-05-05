"""Config flow for the Yandex Smart Home integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Callable, Coroutine, Mapping

from aiohttp import ClientConnectorError, ClientResponseError
from homeassistant.auth.const import GROUP_ID_READ_ONLY
from homeassistant.config_entries import ConfigFlow, OptionsFlow
from homeassistant.const import CONF_ENTITIES, CONF_ID
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowHandler, FlowResult
from homeassistant.helpers import selector
from homeassistant.helpers.entityfilter import CONF_INCLUDE_ENTITIES, EntityFilter
from homeassistant.helpers.selector import (
    BooleanSelector,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)
import voluptuous as vol

from . import DOMAIN, FILTER_SCHEMA, const
from .cloud import register_cloud_instance
from .const import ConnectionType, EntityFilterSource

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers import ConfigType

_LOGGER = logging.getLogger(__name__)

DEFAULT_CONFIG_ENTRY_TITLE = "Yandex Smart Home"
USER_NONE = "none"

CONNECTION_TYPE_SELECTOR = SelectSelector(
    SelectSelectorConfig(
        mode=SelectSelectorMode.LIST,
        translation_key=const.CONF_CONNECTION_TYPE,
        options=[
            SelectOptionDict(value=ConnectionType.CLOUD, label=ConnectionType.CLOUD),
            SelectOptionDict(value=ConnectionType.DIRECT, label=ConnectionType.DIRECT),
        ],
    ),
)
FILTER_SOURCE_SELECTOR = SelectSelector(
    SelectSelectorConfig(
        mode=SelectSelectorMode.LIST,
        translation_key=const.CONF_FILTER_SOURCE,
        options=[
            SelectOptionDict(value=EntityFilterSource.CONFIG_ENTRY, label=EntityFilterSource.CONFIG_ENTRY),
            SelectOptionDict(
                value=EntityFilterSource.GET_FROM_CONFIG_ENTRY, label=EntityFilterSource.GET_FROM_CONFIG_ENTRY
            ),
            SelectOptionDict(value=EntityFilterSource.YAML, label=EntityFilterSource.YAML),
        ],
    ),
)


class BaseFlowHandler(FlowHandler):
    """Handle shared steps between config and options flow for Yandex Smart Home."""

    _async_step_filter_settings_done: Callable[[ConfigType | None], Coroutine[Any, Any, FlowResult]]

    def __init__(self) -> None:
        """Initialize a flow handler."""
        self._options: ConfigType = {}
        self._entry: ConfigEntry | None = None

        super().__init__()

    async def async_step_expose_settings(self, user_input: ConfigType | None = None) -> FlowResult:
        """Choose entity expose settings."""
        if user_input is not None:
            self._options.update(user_input)

            match user_input[const.CONF_FILTER_SOURCE]:
                case EntityFilterSource.CONFIG_ENTRY:
                    return await self.async_step_include_entities()
                case EntityFilterSource.GET_FROM_CONFIG_ENTRY:
                    return await self.async_step_update_filter()

            return await self._async_step_filter_settings_done(None)

        return self.async_show_form(
            step_id="expose_settings",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        const.CONF_FILTER_SOURCE,
                        default=self._options.get(const.CONF_FILTER_SOURCE, EntityFilterSource.CONFIG_ENTRY),
                    ): FILTER_SOURCE_SELECTOR,
                    vol.Required(
                        const.CONF_ENTRY_ALIASES,
                        default=self._options.get(const.CONF_ENTRY_ALIASES, True),
                    ): BooleanSelector(),
                }
            ),
        )

    async def async_step_update_filter(self, user_input: ConfigType | None = None) -> FlowResult:
        """Choose a config entry from which the filter will be copied."""
        if user_input is not None:
            if entry := self.hass.config_entries.async_get_entry(user_input.get(CONF_ID, "")):
                self._options.update(
                    {
                        const.CONF_FILTER_SOURCE: EntityFilterSource.CONFIG_ENTRY,
                        const.CONF_FILTER: entry.options[const.CONF_FILTER],
                    }
                )

                return await self.async_step_include_entities()

        config_entries = [
            entry
            for entry in self.hass.config_entries.async_entries(DOMAIN)
            if const.CONF_FILTER in entry.options and (not self._entry or self._entry.entry_id != entry.entry_id)
        ]
        if not config_entries:
            return self.async_show_form(step_id="update_filter", errors={"base": "missing_config_entry"})

        return self.async_show_form(
            step_id="update_filter",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ID): SelectSelector(
                        SelectSelectorConfig(
                            mode=SelectSelectorMode.LIST,
                            options=[
                                SelectOptionDict(value=entry.entry_id, label=entry.title) for entry in config_entries
                            ],
                        ),
                    )
                }
            ),
        )

    async def async_step_include_entities(self, user_input: ConfigType | None = None) -> FlowResult:
        """Choose entities that should be exposed."""
        errors = {}
        entities: set[str] = set()

        if entity_filter_config := self._options.get(const.CONF_FILTER):
            entities.update(entity_filter_config.get(CONF_INCLUDE_ENTITIES, []))

            if len(entity_filter_config) > 1 or CONF_INCLUDE_ENTITIES not in entity_filter_config:
                entity_filter: EntityFilter = FILTER_SCHEMA(entity_filter_config)
                if not entity_filter.empty_filter:
                    entities.update([s.entity_id for s in self.hass.states.async_all() if entity_filter(s.entity_id)])

        if user_input is not None:
            if user_input[CONF_ENTITIES]:
                self._options[const.CONF_FILTER] = {CONF_INCLUDE_ENTITIES: user_input[CONF_ENTITIES]}

                return await self._async_step_filter_settings_done(None)
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


class ConfigFlowHandler(BaseFlowHandler, ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Yandex Smart Home."""

    VERSION = 4

    def __init__(self) -> None:
        """Initialize a config flow handler."""
        super().__init__()

        self._data: ConfigType = {const.CONF_DEVICES_DISCOVERED: False}
        self._async_step_filter_settings_done = self.async_step_connection_type

    async def async_step_user(  # type: ignore[override]
        self,
        user_input: ConfigType | None = None,
    ) -> FlowResult:
        """Handle a flow initialized by the user."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            return await self.async_step_expose_settings()

        return self.async_show_form(step_id="user")

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
                {vol.Required(const.CONF_CONNECTION_TYPE, default=ConnectionType.CLOUD): CONNECTION_TYPE_SELECTOR}
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(entry: ConfigEntry) -> OptionsFlow:
        """Get the options flow for this handler."""
        return OptionsFlowHandler(entry)


class OptionsFlowHandler(BaseFlowHandler, OptionsFlow):
    """Handle a options flow for Yandex Smart Home."""

    def __init__(self, entry: ConfigEntry):
        """Initialize an options flow handler."""
        super().__init__()

        self._entry: ConfigEntry = entry
        self._data: ConfigType = entry.data.copy()
        self._options: ConfigType = entry.options.copy()
        self._async_step_filter_settings_done = self.async_step_done

    async def async_step_init(self, _: ConfigType | None = None) -> FlowResult:
        """Show menu."""
        options = ["expose_settings", "connection_type"]
        if self._data[const.CONF_CONNECTION_TYPE] == ConnectionType.CLOUD:
            options += ["cloud_info", "context_user"]

        return self.async_show_menu(step_id="init", menu_options=options)

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
                    vol.Required(
                        const.CONF_CONNECTION_TYPE, default=self._data[const.CONF_CONNECTION_TYPE]
                    ): CONNECTION_TYPE_SELECTOR
                }
            ),
            errors=errors,
        )

    async def async_step_context_user(self, user_input: ConfigType | None = None) -> FlowResult:
        """Choose user for a service calls context."""
        if user_input is not None:
            if user_input[const.CONF_USER_ID] == USER_NONE:
                self._options.pop(const.CONF_USER_ID, None)
            else:
                self._options.update(user_input)

            return await self.async_step_done()

        return self.async_show_form(
            step_id="context_user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        const.CONF_USER_ID, default=self._options.get(const.CONF_USER_ID, USER_NONE)
                    ): SelectSelector(
                        SelectSelectorConfig(
                            mode=SelectSelectorMode.LIST,
                            translation_key=const.CONF_USER_ID,
                            options=await _async_get_users(self.hass),
                        ),
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

    async def async_step_done(self, _: ConfigType | None = None) -> FlowResult:
        """Finish the flow."""
        return self.async_create_entry(data=self._options)


async def _async_get_users(hass: HomeAssistant) -> list[SelectOptionDict]:
    """Return users with admin privileges."""
    users: list[SelectOptionDict] = [SelectOptionDict(value=USER_NONE, label=USER_NONE)]

    for user in await hass.auth.async_get_users():
        if any(gr.id == GROUP_ID_READ_ONLY for gr in user.groups):
            continue

        users.append(SelectOptionDict(value=user.id, label=user.name or user.id))

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
