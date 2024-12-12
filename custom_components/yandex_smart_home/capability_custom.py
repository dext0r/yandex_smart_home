"""Implement the Yandex Smart Home user specific capabilities."""

from __future__ import annotations

from functools import cached_property
import itertools
import logging
from typing import TYPE_CHECKING, Any, Iterable, Protocol, Self, cast

from homeassistant.const import CONF_STATE_TEMPLATE, STATE_OFF, STATE_ON, STATE_UNKNOWN
from homeassistant.core import Context, HomeAssistant, callback
from homeassistant.exceptions import TemplateError
from homeassistant.helpers.service import async_call_from_config
from homeassistant.helpers.template import Template, forgiving_boolean
from homeassistant.helpers.typing import UNDEFINED, ConfigType, UndefinedType

from .capability import Capability
from .capability_color import ColorSceneCapability
from .capability_mode import ModeCapability
from .capability_onoff import OnOffCapability, OnOffCapabilityInstanceActionState
from .capability_range import RangeCapability
from .capability_toggle import ToggleCapability
from .const import (
    CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ATTRIBUTE,
    CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ENTITY_ID,
    CONF_ENTITY_CUSTOM_MODE_SET_MODE,
    CONF_ENTITY_CUSTOM_RANGE_DECREASE_VALUE,
    CONF_ENTITY_CUSTOM_RANGE_INCREASE_VALUE,
    CONF_ENTITY_CUSTOM_RANGE_SET_VALUE,
    CONF_ENTITY_CUSTOM_TOGGLE_TURN_OFF,
    CONF_ENTITY_CUSTOM_TOGGLE_TURN_ON,
    CONF_ENTITY_MODE_MAP,
    CONF_ENTITY_RANGE,
    CONF_ENTITY_RANGE_MAX,
    CONF_ENTITY_RANGE_MIN,
    CONF_ENTITY_RANGE_PRECISION,
    CONF_STATE_UNKNOWN,
)
from .helpers import ActionNotAllowed, APIError
from .schema import (
    CapabilityInstance,
    CapabilityType,
    ColorScene,
    ColorSettingCapabilityInstance,
    ModeCapabilityInstance,
    ModeCapabilityInstanceActionState,
    ModeCapabilityMode,
    OnOffCapabilityInstance,
    RangeCapabilityInstance,
    RangeCapabilityInstanceActionState,
    RangeCapabilityRange,
    ResponseCode,
    SceneInstanceActionState,
    ToggleCapabilityInstance,
    ToggleCapabilityInstanceActionState,
)

if TYPE_CHECKING:
    from .entry_data import ConfigEntryData

_LOGGER = logging.getLogger(__name__)


class CustomCapability(Capability[Any], Protocol):
    """Base class for a capability that user can set up using yaml configuration."""

    device_id: str
    instance: CapabilityInstance

    _hass: HomeAssistant
    _entry_data: ConfigEntryData
    _config: ConfigType
    _value_template: Template | None
    _value: Any | UndefinedType

    def __init__(
        self,
        hass: HomeAssistant,
        entry_data: ConfigEntryData,
        config: ConfigType,
        instance: CapabilityInstance,
        device_id: str,
        value_template: Template | None,
        value: Any | UndefinedType = UNDEFINED,
    ):
        """Initialize a custom capability."""
        self._hass = hass
        self._entry_data = entry_data
        self._config = config
        self._value_template = value_template
        self._value = value

        self.device_id = device_id
        self.instance = instance

    # noinspection PyProtocol
    @property
    def retrievable(self) -> bool:
        """Test if the capability can return the current value."""
        return self._value_template is not None

    @property
    def reportable(self) -> bool:
        """Test if the capability can report value changes."""
        if not self.retrievable:
            return False

        return super().reportable

    def new_with_value(self, value: Any) -> Self:
        """Return copy of the state with new value."""
        return self.__class__(
            self._hass,
            self._entry_data,
            self._config,
            self.instance,
            self.device_id,
            self._value_template,
            value,
        )

    @callback
    def _get_source_value(self) -> Any:
        """Return the current capability value (unprocessed)."""
        if self._value_template is None:
            return None

        if self._value is not UNDEFINED:
            return self._value

        try:
            return self._value_template.async_render()
        except TemplateError as exc:
            raise APIError(ResponseCode.INVALID_VALUE, f"Failed to get current value for {self}: {exc!r}")

    def __repr__(self) -> str:
        """Return the representation."""
        return (
            f"<{self.__class__.__name__}"
            f" device_id={self.device_id }"
            f" instance={self.instance}"
            f" value_template={self._value_template}"
            f" value={self._value}"
            f">"
        )


class CustomOnOffCapability(CustomCapability, OnOffCapability):
    """OnOff capability that user can set up using yaml configuration."""

    instance: OnOffCapabilityInstance

    @property
    def supported(self) -> bool:
        """Test if the capability is supported."""
        return True

    @property
    def retrievable(self) -> bool:
        """Test if the capability can return the current value."""
        if self._entity_config.get(CONF_STATE_UNKNOWN):
            return False

        return True

    def get_value(self) -> bool | None:
        """Return the current capability value."""
        if not self.retrievable:
            return None

        if self._value_template is not None:
            return bool(self._get_source_value() == STATE_ON)

        return False

    async def _set_instance_state(self, context: Context, state: OnOffCapabilityInstanceActionState) -> None:
        """Change the capability state (if wasn't overriden by the user)."""
        raise ActionNotAllowed


class CustomModeCapability(CustomCapability, ModeCapability):
    """Mode capability that user can set up using yaml configuration."""

    instance: ModeCapabilityInstance

    def get_value(self) -> ModeCapabilityMode | None:
        """Return the current capability value."""
        if not self.retrievable:
            return None

        if (value := self._get_source_value()) is not None:
            return self.get_yandex_mode_by_ha_mode(str(value))

        return None

    async def set_instance_state(self, context: Context, state: ModeCapabilityInstanceActionState) -> None:
        """Change the capability state."""
        service_config = self._config.get(CONF_ENTITY_CUSTOM_MODE_SET_MODE)
        if not service_config:
            raise ActionNotAllowed

        await async_call_from_config(
            self._hass,
            service_config,
            validate_config=False,
            variables={"mode": self.get_ha_mode_by_yandex_mode(state.value)},
            blocking=self._wait_for_service_call,
            context=context,
        )

    @property
    def _ha_modes(self) -> Iterable[Any]:
        """Returns list of HA modes."""
        modes = self._entity_config.get(CONF_ENTITY_MODE_MAP, {}).get(self.instance, {})
        return itertools.chain(*modes.values())


class CustomToggleCapability(CustomCapability, ToggleCapability):
    """Toggle capability that user can set up using yaml configuration."""

    instance: ToggleCapabilityInstance

    @property
    def supported(self) -> bool:
        """Test if the capability is supported."""
        return True

    def get_value(self) -> bool | None:
        """Return the current capability value."""
        if not self.retrievable:
            return None

        value = self._get_source_value()
        if value is None:
            return None

        return forgiving_boolean(value, None)

    async def set_instance_state(self, context: Context, state: ToggleCapabilityInstanceActionState) -> None:
        """Change the capability state."""
        if state.value:
            service_config = self._config.get(CONF_ENTITY_CUSTOM_TOGGLE_TURN_ON)
        else:
            service_config = self._config.get(CONF_ENTITY_CUSTOM_TOGGLE_TURN_OFF)

        if not service_config:
            raise ActionNotAllowed

        await async_call_from_config(
            self._hass,
            service_config,
            validate_config=False,
            blocking=self._wait_for_service_call,
            context=context,
        )


class CustomRangeCapability(CustomCapability, RangeCapability):
    """Range capability that user can set up using yaml configuration."""

    instance: RangeCapabilityInstance

    @property
    def supported(self) -> bool:
        """Test if the capability is supported."""
        return True

    @property
    def support_random_access(self) -> bool:
        """Test if the capability accept arbitrary values to be set."""
        for key in [CONF_ENTITY_RANGE_MIN, CONF_ENTITY_RANGE_MAX]:
            if key not in self._config.get(CONF_ENTITY_RANGE, {}):
                return False

        return self._set_value_service_config is not None

    async def set_instance_state(self, context: Context, state: RangeCapabilityInstanceActionState) -> None:
        """Change the capability state."""
        service_config = self._set_value_service_config
        value = state.value

        if state.relative:
            if self._increase_value_service_config or self._decrease_value_service_config:
                if state.value > 0:
                    service_config = self._increase_value_service_config
                else:
                    service_config = self._decrease_value_service_config
            else:
                if not self.retrievable:
                    raise APIError(
                        ResponseCode.NOT_SUPPORTED_IN_CURRENT_MODE,
                        f"Unable to set relative value for {self}: no current value source or service found",
                    )

                value = self._get_absolute_value(state.value)

        if not service_config:
            raise ActionNotAllowed

        await async_call_from_config(
            self._hass,
            service_config,
            validate_config=False,
            variables={"value": value},
            blocking=self._wait_for_service_call,
            context=context,
        )

    def _get_value(self) -> float | None:
        """Return the current capability value (unguarded)."""
        if not self.retrievable:
            return None

        return self._convert_to_float(self._get_source_value())

    def _get_absolute_value(self, relative_value: float) -> float:
        """Return the absolute value for a relative value."""
        value = self._get_value()

        if value is None:
            if self._value_template is not None:
                info = self._value_template.async_render_to_info()
                for entity_id in info.entities:
                    state = self._hass.states.get(entity_id)
                    if state is None:
                        raise APIError(ResponseCode.DEVICE_OFF, f"Entity {entity_id} not found")
                    elif state.state in (STATE_OFF, STATE_UNKNOWN):
                        raise APIError(ResponseCode.DEVICE_OFF, f"Device {entity_id} probably turned off")

            raise APIError(ResponseCode.NOT_SUPPORTED_IN_CURRENT_MODE, f"Missing current value for {self}")

        return max(min(value + relative_value, self._range.max), self._range.min)

    @cached_property
    def _range(self) -> RangeCapabilityRange:
        """Return supporting value range."""
        return RangeCapabilityRange(
            min=self._config.get(CONF_ENTITY_RANGE, {}).get(CONF_ENTITY_RANGE_MIN, super()._range.min),
            max=self._config.get(CONF_ENTITY_RANGE, {}).get(CONF_ENTITY_RANGE_MAX, super()._range.max),
            precision=self._config.get(CONF_ENTITY_RANGE, {}).get(
                CONF_ENTITY_RANGE_PRECISION, super()._range.precision
            ),
        )

    @property
    def _set_value_service_config(self) -> ConfigType | None:
        """Return service configuration for setting value action."""
        return self._config.get(CONF_ENTITY_CUSTOM_RANGE_SET_VALUE)

    @property
    def _increase_value_service_config(self) -> ConfigType | None:
        """Return service configuration for setting increase value action."""
        return self._config.get(CONF_ENTITY_CUSTOM_RANGE_INCREASE_VALUE)

    @property
    def _decrease_value_service_config(self) -> ConfigType | None:
        """Return service configuration for setting decrease value action."""
        return self._config.get(CONF_ENTITY_CUSTOM_RANGE_DECREASE_VALUE)


class CustomColorSceneCapability(CustomCapability, ColorSceneCapability):
    """Custom scene capability that user can set up using yaml configuration."""

    @property
    def supported_ha_scenes(self) -> list[str]:
        """Returns a list of supported HA scenes."""
        modes = self._entity_config.get(CONF_ENTITY_MODE_MAP, {}).get(self.instance, {})
        return list(itertools.chain(*modes.values()))

    def get_value(self) -> ColorScene | None:
        """Return the current capability value."""
        if not self.retrievable:
            return None

        if (value := self._get_source_value()) is not None:
            return self.get_yandex_scene_by_ha_scene(str(value))

        return None

    async def set_instance_state(self, context: Context, state: SceneInstanceActionState) -> None:
        """Change the capability state."""
        service_config = self._config.get(CONF_ENTITY_CUSTOM_MODE_SET_MODE)
        if not service_config:
            raise ActionNotAllowed

        await async_call_from_config(
            self._hass,
            service_config,
            validate_config=False,
            variables={"mode": self.get_ha_scene_by_yandex_scene(state.value)},
            blocking=self._wait_for_service_call,
            context=context,
        )


def get_custom_capability(
    hass: HomeAssistant,
    entry_data: ConfigEntryData,
    capability_config: ConfigType,
    capability_type: CapabilityType,
    instance: str,
    device_id: str,
) -> CustomCapability:
    """Return initialized custom capability based on parameters."""
    value_template = get_value_template(hass, device_id, capability_config)

    match capability_type:
        case CapabilityType.ON_OFF:
            return CustomOnOffCapability(
                hass, entry_data, capability_config, OnOffCapabilityInstance(instance), device_id, value_template
            )

        case CapabilityType.MODE:
            if instance == ColorSettingCapabilityInstance.SCENE:
                return CustomColorSceneCapability(
                    hass, entry_data, capability_config, ColorSettingCapabilityInstance.SCENE, device_id, value_template
                )

            return CustomModeCapability(
                hass, entry_data, capability_config, ModeCapabilityInstance(instance), device_id, value_template
            )
        case CapabilityType.TOGGLE:
            return CustomToggleCapability(
                hass, entry_data, capability_config, ToggleCapabilityInstance(instance), device_id, value_template
            )
        case CapabilityType.RANGE:
            return CustomRangeCapability(
                hass, entry_data, capability_config, RangeCapabilityInstance(instance), device_id, value_template
            )

    raise APIError(ResponseCode.INTERNAL_ERROR, f"Unsupported capability type: {capability_type}")


def get_value_template(hass: HomeAssistant, device_id: str, capability_config: ConfigType) -> Template | None:
    """Return capability value template from capability configuration."""
    if template := capability_config.get(CONF_STATE_TEMPLATE):
        return cast(Template, template)

    entity_id = capability_config.get(CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ENTITY_ID)
    attribute = capability_config.get(CONF_ENTITY_CUSTOM_CAPABILITY_STATE_ATTRIBUTE)

    if attribute:
        return Template("{{ state_attr('%s', '%s') }}" % (entity_id or device_id, attribute), hass)
    elif entity_id:
        return Template("{{ states('%s') }}" % entity_id, hass)

    return None
