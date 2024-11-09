"""Config flow for the Yandex Smart Home integration."""

from __future__ import annotations

from enum import StrEnum
import logging
from typing import TYPE_CHECKING, cast

from aiohttp import ClientConnectorError, ClientResponseError
from homeassistant.auth.const import GROUP_ID_READ_ONLY
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_ENTITIES, CONF_ID, CONF_NAME, CONF_PLATFORM, CONF_TOKEN
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import AbortFlow, FlowHandler
from homeassistant.helpers import network, selector
from homeassistant.helpers.entityfilter import CONF_INCLUDE_ENTITIES, EntityFilter
from homeassistant.helpers.selector import (
    BooleanSelector,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
)
from homeassistant.helpers.typing import ConfigType
from homeassistant.setup import async_setup_component
import voluptuous as vol

from . import DOMAIN, FILTER_SCHEMA, SmartHomePlatform, cloud
from .const import (
    CLOUD_BASE_URL,
    CONF_CLOUD_INSTANCE,
    CONF_CLOUD_INSTANCE_CONNECTION_TOKEN,
    CONF_CLOUD_INSTANCE_ID,
    CONF_CLOUD_INSTANCE_PASSWORD,
    CONF_CONNECTION_TYPE,
    CONF_ENTRY_ALIASES,
    CONF_FILTER,
    CONF_FILTER_SOURCE,
    CONF_LINKED_PLATFORMS,
    CONF_SKILL,
    CONF_USER_ID,
    ConnectionType,
    EntityFilterSource,
)

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigFlowContext  # noqa: F401


_LOGGER = logging.getLogger(__name__)

DEFAULT_CONFIG_ENTRY_TITLE = "Yandex Smart Home"
PRE_V1_DIRECT_CONFIG_ENTRY_TITLE = "YSH: Direct"  # TODO: remove after v1.1 release
USER_NONE = "none"


class MaintenanceAction(StrEnum):
    REVOKE_OAUTH_TOKENS = "revoke_oauth_tokens"
    UNLINK_ALL_PLATFORMS = "unlink_all_platforms"
    RESET_CLOUD_INSTANCE_CONNECTION_TOKEN = "reset_cloud_instance_connection_token"


CONNECTION_TYPE_SELECTOR = SelectSelector(
    SelectSelectorConfig(
        mode=SelectSelectorMode.LIST,
        translation_key=CONF_CONNECTION_TYPE,
        options=[
            SelectOptionDict(value=ConnectionType.CLOUD, label=ConnectionType.CLOUD),
            SelectOptionDict(value=ConnectionType.CLOUD_PLUS, label=ConnectionType.CLOUD_PLUS),
            SelectOptionDict(value=ConnectionType.DIRECT, label=ConnectionType.DIRECT),
        ],
    ),
)
PLATFORM_SELECTOR = SelectSelector(
    SelectSelectorConfig(
        mode=SelectSelectorMode.LIST,
        translation_key=CONF_PLATFORM,
        options=[
            SelectOptionDict(value=SmartHomePlatform.YANDEX, label=SmartHomePlatform.YANDEX),
        ],
    ),
)
FILTER_SOURCE_SELECTOR = SelectSelector(
    SelectSelectorConfig(
        mode=SelectSelectorMode.LIST,
        translation_key=CONF_FILTER_SOURCE,
        options=[
            SelectOptionDict(value=EntityFilterSource.CONFIG_ENTRY, label=EntityFilterSource.CONFIG_ENTRY),
            SelectOptionDict(
                value=EntityFilterSource.GET_FROM_CONFIG_ENTRY, label=EntityFilterSource.GET_FROM_CONFIG_ENTRY
            ),
            SelectOptionDict(value=EntityFilterSource.YAML, label=EntityFilterSource.YAML),
        ],
    ),
)


class BaseFlowHandler(FlowHandler["ConfigFlowContext", ConfigFlowResult]):
    """Handle shared steps between config and options flow for Yandex Smart Home."""

    def __init__(self) -> None:
        """Initialize a flow handler."""
        self._options: ConfigType = {}
        self._data: ConfigType = {}
        self._entry: ConfigEntry | None = None

        super().__init__()

    async def async_step_skill_yandex_direct(self, user_input: ConfigType | None = None) -> ConfigFlowResult:
        """Choose skill settings for direct connection to the Yandex Smart Home platform."""
        errors = {}
        description_placeholders = {"external_url": self._get_external_url()}
        entry_skill = self._options.get(CONF_SKILL, {})

        if DOMAIN not in self.hass.data:
            await async_setup_component(self.hass, DOMAIN, {})  # expose http endpoints for skill validation

        if user_input is not None:
            if existed_entry := self._get_direct_connection_entry(
                platform=SmartHomePlatform.YANDEX,
                user_id=user_input[CONF_USER_ID],
            ):
                description_placeholders["entry_title"] = existed_entry.title
                errors["base"] = "already_configured"
            else:
                self._options[CONF_SKILL] = user_input

                if self._entry:
                    if user_input[CONF_ID] != entry_skill.get(CONF_ID) or user_input[CONF_USER_ID] != entry_skill.get(
                        CONF_USER_ID
                    ):
                        self._data[CONF_LINKED_PLATFORMS] = []
                        self.hass.config_entries.async_update_entry(
                            self._entry,
                            title=await async_config_entry_title(self.hass, self._data, self._options),
                            data=self._data,
                        )

                    return await self.async_step_done()

                return await self.async_step_expose_settings()

        return self.async_show_form(
            step_id="skill_yandex_direct",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USER_ID, default=entry_skill.get(CONF_USER_ID)): await _async_get_user_selector(
                        self.hass, mode=SelectSelectorMode.DROPDOWN, required=True
                    ),
                    vol.Required(CONF_ID, default=entry_skill.get(CONF_ID)): TextSelector(),
                    vol.Required(CONF_TOKEN, default=entry_skill.get(CONF_TOKEN)): TextSelector(),
                },
            ),
            errors=errors,
            description_placeholders=description_placeholders,
        )

    async def async_step_skill_yandex_cloud_plus(self, user_input: ConfigType | None = None) -> ConfigFlowResult:
        """Choose skill settings for cloud plus connection to the Yandex Smart Home platform."""
        errors: dict[str, str] = {}
        description_placeholders = {
            "cloud_base_url": CLOUD_BASE_URL,
            "instance_id": self._data[CONF_CLOUD_INSTANCE][CONF_CLOUD_INSTANCE_ID],
        }
        entry_skill = self._options.get(CONF_SKILL, {})

        if user_input is not None:
            self._options[CONF_SKILL] = user_input

            if self._entry:
                if user_input[CONF_ID] != entry_skill.get(CONF_ID):
                    self._data[CONF_LINKED_PLATFORMS] = []

                if user_input[CONF_ID] != entry_skill.get(CONF_ID) or user_input[CONF_NAME] != entry_skill.get(
                    CONF_NAME
                ):
                    self.hass.config_entries.async_update_entry(
                        self._entry,
                        title=await async_config_entry_title(self.hass, self._data, self._options),
                        data=self._data,
                    )

                return await self.async_step_done()

            return await self.async_step_expose_settings()

        return self.async_show_form(
            step_id="skill_yandex_cloud_plus",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME, default=entry_skill.get(CONF_NAME)): TextSelector(),
                    vol.Required(CONF_ID, default=entry_skill.get(CONF_ID)): TextSelector(),
                    vol.Required(CONF_TOKEN, default=entry_skill.get(CONF_TOKEN)): TextSelector(),
                },
            ),
            errors=errors,
            description_placeholders=description_placeholders,
        )

    async def async_step_expose_settings(self, user_input: ConfigType | None = None) -> ConfigFlowResult:
        """Choose entity expose settings."""
        if user_input is not None:
            self._options.update(user_input)

            match user_input[CONF_FILTER_SOURCE]:
                case EntityFilterSource.CONFIG_ENTRY:
                    return await self.async_step_include_entities()
                case EntityFilterSource.GET_FROM_CONFIG_ENTRY:
                    return await self.async_step_update_filter()

            return await self.async_step_done()

        return self.async_show_form(
            step_id="expose_settings",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_FILTER_SOURCE,
                        default=self._options.get(CONF_FILTER_SOURCE, EntityFilterSource.CONFIG_ENTRY),
                    ): FILTER_SOURCE_SELECTOR,
                    vol.Required(
                        CONF_ENTRY_ALIASES,
                        default=self._options.get(CONF_ENTRY_ALIASES, True),
                    ): BooleanSelector(),
                }
            ),
        )

    async def async_step_update_filter(self, user_input: ConfigType | None = None) -> ConfigFlowResult:
        """Choose a config entry from which the filter will be copied."""
        if user_input is not None:
            if entry := self.hass.config_entries.async_get_entry(user_input.get(CONF_ID, "")):
                self._options.update(
                    {
                        CONF_FILTER_SOURCE: EntityFilterSource.CONFIG_ENTRY,
                        CONF_FILTER: entry.options[CONF_FILTER],
                    }
                )

                return await self.async_step_include_entities()

        config_entries = [
            entry
            for entry in self.hass.config_entries.async_entries(DOMAIN)
            if CONF_FILTER in entry.options and (not self._entry or self._entry.entry_id != entry.entry_id)
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

    async def async_step_include_entities(self, user_input: ConfigType | None = None) -> ConfigFlowResult:
        """Choose entities that should be exposed."""
        errors = {}
        entities: set[str] = set()

        if entity_filter_config := self._options.get(CONF_FILTER):
            entities.update(entity_filter_config.get(CONF_INCLUDE_ENTITIES, []))

            if len(entity_filter_config) > 1 or CONF_INCLUDE_ENTITIES not in entity_filter_config:
                entity_filter: EntityFilter = FILTER_SCHEMA(entity_filter_config)
                if not entity_filter.empty_filter:
                    entities.update([s.entity_id for s in self.hass.states.async_all() if entity_filter(s.entity_id)])

        if user_input is not None:
            if user_input[CONF_ENTITIES]:
                self._options[CONF_FILTER] = {CONF_INCLUDE_ENTITIES: user_input[CONF_ENTITIES]}
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

    async def async_step_done(self, _: ConfigType | None = None) -> ConfigFlowResult:
        """Finish the flow."""
        raise NotImplementedError

    @callback
    def _get_direct_connection_entry(self, platform: SmartHomePlatform, user_id: str) -> ConfigEntry | None:
        """Return already configured config entry with direct connection."""
        for entry in self.hass.config_entries.async_entries(DOMAIN):
            if self._entry and self._entry.entry_id == entry.entry_id:
                continue

            if CONF_SKILL in entry.options:
                if (
                    ConnectionType.DIRECT == entry.data[CONF_CONNECTION_TYPE]
                    and platform == entry.data[CONF_PLATFORM]
                    and user_id == entry.options[CONF_SKILL][CONF_USER_ID]
                ):
                    return entry

        return None

    def _get_external_url(self) -> str:
        """Return external URL or abort the flow."""
        try:
            return network.get_url(self.hass, allow_internal=False)
        except network.NoURLAvailableError:
            raise AbortFlow("missing_external_url")


class ConfigFlowHandler(BaseFlowHandler, ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Yandex Smart Home."""

    VERSION = 6

    def __init__(self) -> None:
        """Initialize a config flow handler."""
        super().__init__()

        self._data: ConfigType = {}

    async def async_step_user(self, user_input: ConfigType | None = None) -> ConfigFlowResult:
        """Handle a flow initialized by the user."""
        if user_input is not None:
            return await self.async_step_connection_type()

        return self.async_show_form(step_id="user")

    async def async_step_connection_type(self, user_input: ConfigType | None = None) -> ConfigFlowResult:
        """Choose connection type."""
        errors = {}
        if user_input is not None:
            self._data.update(user_input)

            if user_input[CONF_CONNECTION_TYPE] in (ConnectionType.CLOUD, ConnectionType.CLOUD_PLUS):
                try:
                    instance = await cloud.register_instance(self.hass)
                    self._data[CONF_CLOUD_INSTANCE] = {
                        CONF_CLOUD_INSTANCE_ID: instance.id,
                        CONF_CLOUD_INSTANCE_PASSWORD: instance.password,
                        CONF_CLOUD_INSTANCE_CONNECTION_TOKEN: instance.connection_token,
                    }
                except (ClientConnectorError, ClientResponseError):
                    errors["base"] = "cannot_connect"
                    _LOGGER.exception("Failed to register instance in Yandex Smart Home cloud")

            if not errors:
                match user_input[CONF_CONNECTION_TYPE]:
                    case ConnectionType.DIRECT:
                        return await self.async_step_platform_direct()
                    case ConnectionType.CLOUD_PLUS:
                        return await self.async_step_platform_cloud_plus()

                return await self.async_step_expose_settings()

        return self.async_show_form(
            step_id="connection_type",
            data_schema=vol.Schema(
                {vol.Required(CONF_CONNECTION_TYPE, default=ConnectionType.CLOUD): CONNECTION_TYPE_SELECTOR}
            ),
            errors=errors,
        )

    async def async_step_platform_direct(self, user_input: ConfigType | None = None) -> ConfigFlowResult:
        """Choose smart home platform for direct connection."""
        if user_input is not None:
            self._data.update(user_input)
            step_fn = getattr(self, f"async_step_skill_{self._data[CONF_PLATFORM]}_direct")
            return cast(ConfigFlowResult, await step_fn())

        return self.async_show_form(
            step_id="platform_direct",
            description_placeholders={"external_url": self._get_external_url()},
            data_schema=vol.Schema({vol.Required(CONF_PLATFORM): PLATFORM_SELECTOR}),
        )

    async def async_step_platform_cloud_plus(self, user_input: ConfigType | None = None) -> ConfigFlowResult:
        """Choose smart home platform for cloud p connection."""
        if user_input is not None:
            self._data.update(user_input)
            step_fn = getattr(self, f"async_step_skill_{self._data[CONF_PLATFORM]}_cloud_plus")
            return cast(ConfigFlowResult, await step_fn())

        return self.async_show_form(
            step_id="platform_cloud_plus",
            data_schema=vol.Schema({vol.Required(CONF_PLATFORM): PLATFORM_SELECTOR}),
        )

    async def async_step_done(self, _: ConfigType | None = None) -> ConfigFlowResult:
        """Finish the flow."""
        description_placeholders: dict[str, str] = self._data.get(CONF_CLOUD_INSTANCE, {}).copy()
        if self._data[CONF_CONNECTION_TYPE] == ConnectionType.CLOUD_PLUS:
            description_placeholders[CONF_SKILL] = self._options[CONF_SKILL][CONF_NAME]

        return self.async_create_entry(
            title=await async_config_entry_title(self.hass, self._data, self._options),
            description=self._data[CONF_CONNECTION_TYPE],
            description_placeholders=description_placeholders,
            data=self._data,
            options=self._options,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(OptionsFlow, BaseFlowHandler):
    """Handle a options flow for Yandex Smart Home."""

    def __init__(self, entry: ConfigEntry):
        """Initialize an options flow handler."""
        super().__init__()

        self._entry: ConfigEntry = entry
        self._data: ConfigType = entry.data.copy()
        self._options: ConfigType = entry.options.copy()

    async def async_step_init(self, _: ConfigType | None = None) -> ConfigFlowResult:
        """Show menu."""
        options = ["expose_settings"]
        match self._data[CONF_CONNECTION_TYPE]:
            case ConnectionType.CLOUD:
                options += ["cloud_credentials", "context_user"]
            case ConnectionType.CLOUD_PLUS:
                options += ["cloud_credentials", f"skill_{self._data[CONF_PLATFORM]}_cloud_plus", "context_user"]
            case ConnectionType.DIRECT:
                options += [f"skill_{self._data[CONF_PLATFORM]}_direct"]
        options += ["maintenance"]

        return self.async_show_menu(step_id="init", menu_options=options)

    async def async_step_cloud_credentials(self, user_input: ConfigType | None = None) -> ConfigFlowResult:
        """Show cloud connection credentials."""
        if user_input is not None:
            return await self.async_step_init()

        description_placeholders = {
            CONF_SKILL: "Yaha Cloud",
            CONF_CLOUD_INSTANCE_ID: self._data[CONF_CLOUD_INSTANCE][CONF_CLOUD_INSTANCE_ID],
            CONF_CLOUD_INSTANCE_PASSWORD: self._data[CONF_CLOUD_INSTANCE][CONF_CLOUD_INSTANCE_PASSWORD],
        }
        if self._data[CONF_CONNECTION_TYPE] == ConnectionType.CLOUD_PLUS:
            description_placeholders[CONF_SKILL] = self._options[CONF_SKILL][CONF_NAME]

        return self.async_show_form(step_id="cloud_credentials", description_placeholders=description_placeholders)

    async def async_step_context_user(self, user_input: ConfigType | None = None) -> ConfigFlowResult:
        """Choose user for a service calls context."""
        if user_input is not None:
            if user_input[CONF_USER_ID] == USER_NONE:
                self._options.pop(CONF_USER_ID, None)
            else:
                self._options.update(user_input)

            return await self.async_step_done()

        return self.async_show_form(
            step_id="context_user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_USER_ID, default=self._options.get(CONF_USER_ID, USER_NONE)
                    ): await _async_get_user_selector(self.hass)
                }
            ),
        )

    async def async_step_maintenance(self, user_input: ConfigType | None = None) -> ConfigFlowResult:
        """Show maintenance actions."""
        errors: dict[str, str] = {}
        description_placeholders = {}

        if user_input is not None:
            if user_input.get(MaintenanceAction.REVOKE_OAUTH_TOKENS):
                match self._data[CONF_CONNECTION_TYPE]:
                    case ConnectionType.CLOUD:
                        try:
                            await cloud.revoke_oauth_tokens(
                                self.hass,
                                self._data[CONF_CLOUD_INSTANCE][CONF_CLOUD_INSTANCE_ID],
                                self._data[CONF_CLOUD_INSTANCE][CONF_CLOUD_INSTANCE_CONNECTION_TOKEN],
                            )
                        except Exception as e:
                            errors[MaintenanceAction.REVOKE_OAUTH_TOKENS] = "unknown"
                            description_placeholders["error"] = str(e)

                    case ConnectionType.DIRECT:
                        errors[MaintenanceAction.REVOKE_OAUTH_TOKENS] = "manual_revoke_oauth_tokens"

            if user_input.get(MaintenanceAction.UNLINK_ALL_PLATFORMS):
                self._data[CONF_LINKED_PLATFORMS] = []
                self.hass.config_entries.async_update_entry(self._entry, data=self._data)

            if user_input.get(MaintenanceAction.RESET_CLOUD_INSTANCE_CONNECTION_TOKEN):
                try:
                    instance = await cloud.reset_connection_token(
                        self.hass,
                        self._data[CONF_CLOUD_INSTANCE][CONF_CLOUD_INSTANCE_ID],
                        self._data[CONF_CLOUD_INSTANCE][CONF_CLOUD_INSTANCE_CONNECTION_TOKEN],
                    )
                    self._data[CONF_CLOUD_INSTANCE] = {
                        CONF_CLOUD_INSTANCE_ID: instance.id,
                        CONF_CLOUD_INSTANCE_PASSWORD: self._data[CONF_CLOUD_INSTANCE][CONF_CLOUD_INSTANCE_PASSWORD],
                        CONF_CLOUD_INSTANCE_CONNECTION_TOKEN: instance.connection_token,
                    }
                    self.hass.config_entries.async_update_entry(self._entry, data=self._data)
                except Exception as e:
                    errors[MaintenanceAction.RESET_CLOUD_INSTANCE_CONNECTION_TOKEN] = "unknown"
                    description_placeholders["error"] = str(e)

            if not errors:
                return await self.async_step_done()

        actions = [MaintenanceAction.REVOKE_OAUTH_TOKENS, MaintenanceAction.UNLINK_ALL_PLATFORMS]
        if self._data[CONF_CONNECTION_TYPE] in (ConnectionType.CLOUD, ConnectionType.CLOUD_PLUS):
            actions += [MaintenanceAction.RESET_CLOUD_INSTANCE_CONNECTION_TOKEN]

        return self.async_show_form(
            step_id="maintenance",
            data_schema=vol.Schema({vol.Optional(action.value): BooleanSelector() for action in actions}),
            errors=errors,
            description_placeholders=description_placeholders,
        )

    async def async_step_done(self, _: ConfigType | None = None) -> ConfigFlowResult:
        """Finish the flow."""
        return self.async_create_entry(data=self._options)


async def _async_get_user_selector(
    hass: HomeAssistant, mode: SelectSelectorMode = SelectSelectorMode.LIST, required: bool = False
) -> SelectSelector:
    """Return user selector."""
    users: list[SelectOptionDict] = []
    if not required:
        users.append(SelectOptionDict(value=USER_NONE, label=USER_NONE))

    for user in await hass.auth.async_get_users():
        if any(gr.id == GROUP_ID_READ_ONLY for gr in user.groups):
            continue

        users.append(SelectOptionDict(value=user.id, label=user.name or user.id))

    return SelectSelector(
        SelectSelectorConfig(
            mode=mode,
            translation_key=CONF_USER_ID,
            options=users,
        ),
    )


async def async_config_entry_title(hass: HomeAssistant, data: ConfigType, options: ConfigType) -> str:
    """Return config entry title."""
    if data.get(CONF_CONNECTION_TYPE) == ConnectionType.CLOUD:
        instance_id = data[CONF_CLOUD_INSTANCE][CONF_CLOUD_INSTANCE_ID]
        return f"Yaha Cloud ({instance_id[:8]})"

    title = DEFAULT_CONFIG_ENTRY_TITLE
    connection_type = ""
    match data.get(CONF_CONNECTION_TYPE):
        case ConnectionType.CLOUD_PLUS:
            connection_type = "Cloud Plus"
        case ConnectionType.DIRECT:
            connection_type = "Direct"

    match data.get(CONF_PLATFORM):
        case SmartHomePlatform.YANDEX:
            title = f"Yandex Smart Home: {connection_type}"

    if skill := options.get(CONF_SKILL):
        parts: list[str] = []
        if user := await hass.auth.async_get_user(skill.get(CONF_USER_ID, "")):
            parts.append(user.name or user.id[:6])
        if skill_id := skill.get(CONF_ID, ""):
            parts.append(skill_id[:8])

        title += f' ({" / ".join(parts)})'

    return title
