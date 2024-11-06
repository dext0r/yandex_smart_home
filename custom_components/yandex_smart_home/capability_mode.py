"""Implement the Yandex Smart Home mode capabilities."""

from abc import ABC, abstractmethod
import logging
import math
from typing import Any, Iterable, Protocol

from homeassistant.components import climate, fan, humidifier, media_player, vacuum
from homeassistant.const import ATTR_ENTITY_ID, STATE_OFF, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import Context
from homeassistant.util.percentage import ordered_list_item_to_percentage, percentage_to_ordered_list_item

from . import const
from .capability import STATE_CAPABILITIES_REGISTRY, Capability, StateCapability
from .const import CONF_ENTITY_MODE_MAP, STATE_NONE, MediaPlayerFeature
from .helpers import APIError
from .schema import (
    CapabilityType,
    ModeCapabilityInstance,
    ModeCapabilityInstanceActionState,
    ModeCapabilityMode,
    ModeCapabilityParameters,
    ResponseCode,
)

_LOGGER = logging.getLogger(__name__)


class ModeCapability(Capability[ModeCapabilityInstanceActionState], Protocol):
    """Base class for capabilities with mode functionality like thermostat mode or fan speed.

    https://yandex.ru/dev/dialogs/alice/doc/smart-home/concepts/mode-docpage/
    """

    type: CapabilityType = CapabilityType.MODE
    instance: ModeCapabilityInstance

    _modes_map_default: dict[ModeCapabilityMode, list[str]] = {}
    _modes_map_index_fallback: dict[int, ModeCapabilityMode] = {
        0: ModeCapabilityMode.ONE,
        1: ModeCapabilityMode.TWO,
        2: ModeCapabilityMode.THREE,
        3: ModeCapabilityMode.FOUR,
        4: ModeCapabilityMode.FIVE,
        5: ModeCapabilityMode.SIX,
        6: ModeCapabilityMode.SEVEN,
        7: ModeCapabilityMode.EIGHT,
        8: ModeCapabilityMode.NINE,
        9: ModeCapabilityMode.TEN,
    }

    @property
    def supported(self) -> bool:
        """Test if the capability is supported."""
        return bool(self.supported_yandex_modes)

    @property
    def parameters(self) -> ModeCapabilityParameters:
        """Return parameters for a devices list request."""
        return ModeCapabilityParameters.from_list(self.instance, self.supported_yandex_modes)

    @property
    def supported_yandex_modes(self) -> list[ModeCapabilityMode]:
        """Returns a list of supported Yandex modes."""
        modes = set()
        for ha_value in self.supported_ha_modes:
            if value := self.get_yandex_mode_by_ha_mode(ha_value, hide_warnings=True):
                modes.add(value)

        return sorted(modes)

    @property
    def supported_ha_modes(self) -> list[str]:
        """Returns list of supported HA modes."""
        return list(map(str, self._ha_modes))

    @property
    def modes_map(self) -> dict[ModeCapabilityMode, list[str]]:
        """Return a modes mapping between Yandex and HA."""
        return self.modes_map_config or self._modes_map_default

    @property
    def modes_map_config(self) -> dict[ModeCapabilityMode, list[str]] | None:
        """Return a modes mapping from a entity configuration."""
        if CONF_ENTITY_MODE_MAP in self._entity_config:
            return {
                ModeCapabilityMode(k): v
                for k, v in self._entity_config[CONF_ENTITY_MODE_MAP].get(self.instance, {}).items()
            }

        return None

    def get_yandex_mode_by_ha_mode(self, ha_mode: str, hide_warnings: bool = False) -> ModeCapabilityMode | None:
        """Return Yandex mode for HA mode."""
        mode = None
        for yandex_mode, names in self.modes_map.items():
            if ha_mode.lower() in [n.lower() for n in names]:
                mode = yandex_mode
                break

        if mode is not None and ha_mode not in self.supported_ha_modes:
            raise APIError(
                ResponseCode.INVALID_VALUE,
                f"Unsupported HA mode '{ha_mode}' for {self}: not in {self.supported_ha_modes}",
            )

        if mode is None:
            if self.modes_map_config is None and ha_mode.lower() != STATE_OFF:
                try:
                    mode = self._modes_map_index_fallback[self.supported_ha_modes.index(ha_mode)]
                except (IndexError, ValueError, KeyError):
                    pass

        if mode is None and not hide_warnings:
            if ha_mode.lower() not in (STATE_OFF, STATE_UNAVAILABLE, STATE_UNKNOWN, STATE_NONE):
                if ha_mode.lower() in [m.lower() for m in self.supported_ha_modes]:
                    _LOGGER.warning(
                        f"Failed to get Yandex mode for mode '{ha_mode}' for {self}. "
                        f"It may cause inconsistencies between Yandex and HA. "
                        f"See https://docs.yaha-cloud.ru/master/config/modes/"
                    )

        return mode

    def get_ha_mode_by_yandex_mode(self, yandex_mode: ModeCapabilityMode) -> str:
        """Return HA mode for Yandex mode."""
        ha_modes = self.modes_map.get(yandex_mode, [])
        for ha_mode in ha_modes:
            for am in self.supported_ha_modes:
                if am.lower() == ha_mode.lower():
                    return am

        if self.modes_map_config is None:
            for ha_idx, yandex_mode_idx in self._modes_map_index_fallback.items():
                if yandex_mode_idx == yandex_mode:
                    return self.supported_ha_modes[ha_idx]

        raise APIError(
            ResponseCode.INVALID_VALUE,
            f"Unsupported mode '{yandex_mode}' for {self}, see https://docs.yaha-cloud.ru/master/config/modes/",
        )

    @abstractmethod
    def get_value(self) -> ModeCapabilityMode | None:
        """Return the current capability value."""
        ...

    @property
    @abstractmethod
    def _ha_modes(self) -> Iterable[Any]:
        """Returns list of HA modes."""
        ...


class StateModeCapability(ModeCapability, StateCapability[ModeCapabilityInstanceActionState], Protocol):
    """Base class for a mode capability based on the state."""

    def get_value(self) -> ModeCapabilityMode | None:
        """Return the current capability value."""
        if self._ha_value is None:
            return None

        return self.get_yandex_mode_by_ha_mode(str(self._ha_value), False)

    @property
    def _ha_value(self) -> Any:
        """Return the current unmapped capability value."""
        return self.state.state


@STATE_CAPABILITIES_REGISTRY.register
class ThermostatCapability(StateModeCapability):
    """Capability to control mode of a climate device."""

    instance = ModeCapabilityInstance.THERMOSTAT

    _modes_map_default = {
        ModeCapabilityMode.HEAT: [climate.HVACMode.HEAT],
        ModeCapabilityMode.COOL: [climate.HVACMode.COOL],
        ModeCapabilityMode.AUTO: [climate.HVACMode.HEAT_COOL, climate.HVACMode.AUTO],
        ModeCapabilityMode.DRY: [climate.HVACMode.DRY],
        ModeCapabilityMode.FAN_ONLY: [climate.HVACMode.FAN_ONLY],
    }

    @property
    def supported(self) -> bool:
        """Test if the capability is supported."""
        if self.state.domain == climate.DOMAIN:
            return super().supported

        return False

    async def set_instance_state(self, context: Context, state: ModeCapabilityInstanceActionState) -> None:
        """Change the capability state."""
        await self._hass.services.async_call(
            climate.DOMAIN,
            climate.SERVICE_SET_HVAC_MODE,
            {
                ATTR_ENTITY_ID: self.state.entity_id,
                climate.ATTR_HVAC_MODE: self.get_ha_mode_by_yandex_mode(state.value),
            },
            blocking=True,
            context=context,
        )

    @property
    def _ha_modes(self) -> Iterable[Any]:
        """Returns list of HA modes."""
        return self.state.attributes.get(climate.ATTR_HVAC_MODES, []) or []


@STATE_CAPABILITIES_REGISTRY.register
class SwingCapability(StateModeCapability):
    """Capability to control swing mode of a climate device."""

    instance = ModeCapabilityInstance.SWING

    _modes_map_default = {
        ModeCapabilityMode.VERTICAL: [climate.const.SWING_VERTICAL, "ud"],
        ModeCapabilityMode.HORIZONTAL: [climate.const.SWING_HORIZONTAL, "lr"],
        ModeCapabilityMode.STATIONARY: [climate.const.SWING_OFF],
        ModeCapabilityMode.AUTO: [climate.const.SWING_BOTH, "all"],
    }

    @property
    def supported(self) -> bool:
        """Test if the capability is supported."""
        if self.state.domain == climate.DOMAIN and self._state_features & climate.ClimateEntityFeature.SWING_MODE:
            return super().supported

        return False

    async def set_instance_state(self, context: Context, state: ModeCapabilityInstanceActionState) -> None:
        """Change the capability state."""
        await self._hass.services.async_call(
            climate.DOMAIN,
            climate.SERVICE_SET_SWING_MODE,
            {
                ATTR_ENTITY_ID: self.state.entity_id,
                climate.ATTR_SWING_MODE: self.get_ha_mode_by_yandex_mode(state.value),
            },
            blocking=True,
            context=context,
        )

    @property
    def _ha_modes(self) -> Iterable[Any]:
        """Returns list of HA modes."""
        return self.state.attributes.get(climate.ATTR_SWING_MODES, []) or []

    @property
    def _ha_value(self) -> Any:
        """Return the current unmapped capability value."""
        return self.state.attributes.get(climate.ATTR_SWING_MODE)


class ProgramCapability(StateModeCapability, ABC):
    """Base capability to control a device program."""

    instance = ModeCapabilityInstance.PROGRAM


@STATE_CAPABILITIES_REGISTRY.register
class ProgramCapabilityHumidifier(ProgramCapability):
    """Capability to control the mode of a humidifier device."""

    _modes_map_default = {
        ModeCapabilityMode.FAN_ONLY: [
            const.XIAOMI_AIRPURIFIER_PRESET_FAN,
        ],
        ModeCapabilityMode.AUTO: [
            humidifier.const.MODE_AUTO,
            const.XIAOMI_HUMIDIFIER_CONST_HUMIDITY,
        ],
        ModeCapabilityMode.ECO: [
            humidifier.const.MODE_ECO,
            const.XIAOMI_AIRPURIFIER_PRESET_IDLE,
        ],
        ModeCapabilityMode.QUIET: [
            humidifier.const.MODE_SLEEP,
            const.XIAOMI_AIRPURIFIER_PRESET_SILENT,
        ],
        ModeCapabilityMode.LOW: [
            const.XIAOMI_AIRPURIFIER_PRESET_LOW,
        ],
        ModeCapabilityMode.MIN: [humidifier.const.MODE_AWAY],
        ModeCapabilityMode.MEDIUM: [
            humidifier.const.MODE_COMFORT,
            const.XIAOMI_AIRPURIFIER_PRESET_MEDIUM,
            const.XIAOMI_AIRPURIFIER_PRESET_MIDDLE,
            const.XIAOMI_HUMIDIFIER_PRESET_MID,
        ],
        ModeCapabilityMode.NORMAL: [
            humidifier.const.MODE_NORMAL,
            const.XIAOMI_AIRPURIFIER_PRESET_FAVORITE,
        ],
        ModeCapabilityMode.MAX: [
            humidifier.const.MODE_HOME,
        ],
        ModeCapabilityMode.HIGH: [
            humidifier.const.MODE_BABY,
            const.XIAOMI_AIRPURIFIER_PRESET_HIGH,
        ],
        ModeCapabilityMode.TURBO: [
            humidifier.const.MODE_BOOST,
            const.XIAOMI_AIRPURIFIER_PRESET_STRONG,
        ],
    }

    @property
    def supported(self) -> bool:
        """Test if the capability is supported."""
        if self.state.domain == humidifier.DOMAIN and self._state_features & humidifier.HumidifierEntityFeature.MODES:
            return super().supported

        return False

    async def set_instance_state(self, context: Context, state: ModeCapabilityInstanceActionState) -> None:
        """Change the capability state."""
        await self._hass.services.async_call(
            humidifier.DOMAIN,
            humidifier.SERVICE_SET_MODE,
            {
                ATTR_ENTITY_ID: self.state.entity_id,
                humidifier.ATTR_MODE: self.get_ha_mode_by_yandex_mode(state.value),
            },
            blocking=True,
            context=context,
        )

    @property
    def _ha_modes(self) -> Iterable[Any]:
        """Returns list of HA modes."""
        return self.state.attributes.get(humidifier.ATTR_AVAILABLE_MODES, []) or []

    @property
    def _ha_value(self) -> Any:
        """Return the current unmapped capability value."""
        return self.state.attributes.get(humidifier.ATTR_MODE)


@STATE_CAPABILITIES_REGISTRY.register
class ProgramCapabilityFan(ProgramCapability):
    """Capability to control the mode preset of a fan device."""

    _modes_map_default = {
        ModeCapabilityMode.AUTO: [
            climate.const.FAN_AUTO,
        ],
        ModeCapabilityMode.ECO: [
            const.XIAOMI_AIRPURIFIER_PRESET_IDLE,
        ],
        ModeCapabilityMode.QUIET: [
            const.XIAOMI_AIRPURIFIER_PRESET_SILENT,
            const.XIAOMI_FAN_PRESET_LEVEL_1,
            const.XIAOMI_FAN_PRESET_NATURE,
        ],
        ModeCapabilityMode.LOW: [
            const.XIAOMI_AIRPURIFIER_PRESET_LOW,
            const.XIAOMI_FAN_PRESET_LEVEL_2,
        ],
        ModeCapabilityMode.MEDIUM: [
            const.XIAOMI_HUMIDIFIER_PRESET_MID,
            const.XIAOMI_FAN_PRESET_LEVEL_3,
        ],
        ModeCapabilityMode.NORMAL: [
            const.XIAOMI_FAN_PRESET_NORMAL,
            const.XIAOMI_AIRPURIFIER_PRESET_FAVORITE,
        ],
        ModeCapabilityMode.HIGH: [
            const.XIAOMI_FAN_PRESET_LEVEL_4,
        ],
        ModeCapabilityMode.TURBO: [
            const.XIAOMI_AIRPURIFIER_PRESET_STRONG,
            const.XIAOMI_FAN_PRESET_LEVEL_5,
        ],
    }

    @property
    def supported(self) -> bool:
        """Test if the capability is supported."""
        if self.state.domain == fan.DOMAIN:
            if self._state_features & fan.FanEntityFeature.PRESET_MODE:
                if (
                    self._state_features & fan.FanEntityFeature.SET_SPEED
                    and fan.ATTR_PERCENTAGE_STEP in self.state.attributes
                ):
                    return super().supported

        return False

    async def set_instance_state(self, context: Context, state: ModeCapabilityInstanceActionState) -> None:
        """Change the capability state."""
        await self._hass.services.async_call(
            fan.DOMAIN,
            fan.SERVICE_SET_PRESET_MODE,
            {
                ATTR_ENTITY_ID: self.state.entity_id,
                fan.ATTR_PRESET_MODE: self.get_ha_mode_by_yandex_mode(state.value),
            },
            blocking=True,
            context=context,
        )

    @property
    def _ha_modes(self) -> Iterable[Any]:
        """Returns list of HA modes."""
        return self.state.attributes.get(fan.ATTR_PRESET_MODES, []) or []

    @property
    def _ha_value(self) -> Any:
        """Return the current unmapped capability value."""
        return self.state.attributes.get(fan.ATTR_PRESET_MODE)


@STATE_CAPABILITIES_REGISTRY.register
class InputSourceCapability(StateModeCapability):
    """Capability to control the input source of a media player device."""

    instance = ModeCapabilityInstance.INPUT_SOURCE

    @property
    def supported(self) -> bool:
        """Test if the capability is supported."""
        if self.state.domain == media_player.DOMAIN:
            if MediaPlayerFeature.SELECT_SOURCE in self._entity_config.get(const.CONF_FEATURES, []):
                return super().supported

            if self._state_features & media_player.MediaPlayerEntityFeature.SELECT_SOURCE:
                return super().supported

        return False

    def get_yandex_mode_by_ha_mode(self, ha_mode: str, hide_warnings: bool = False) -> ModeCapabilityMode | None:
        """Return Yandex mode for HA mode."""
        return super().get_yandex_mode_by_ha_mode(ha_mode, hide_warnings=True)

    async def set_instance_state(self, context: Context, state: ModeCapabilityInstanceActionState) -> None:
        """Change the capability state."""
        await self._hass.services.async_call(
            media_player.DOMAIN,
            media_player.SERVICE_SELECT_SOURCE,
            {
                ATTR_ENTITY_ID: self.state.entity_id,
                media_player.ATTR_INPUT_SOURCE: self.get_ha_mode_by_yandex_mode(state.value),
            },
            blocking=True,
            context=context,
        )

    @property
    def _ha_modes(self) -> Iterable[Any]:
        """Returns list of HA modes."""
        modes = self.state.attributes.get(media_player.ATTR_INPUT_SOURCE_LIST, []) or []
        filtered_modes = list(filter(lambda m: m not in ["Live TV"], modes))  # #418
        if filtered_modes or self.state.state not in (STATE_OFF, STATE_UNKNOWN):
            self._cache.save_attr_value(self.state.entity_id, media_player.ATTR_INPUT_SOURCE_LIST, modes)
            return modes

        return self._cache.get_attr_value(self.state.entity_id, media_player.ATTR_INPUT_SOURCE_LIST) or []

    @property
    def _ha_value(self) -> Any:
        """Return the current unmapped capability value."""
        return self.state.attributes.get(media_player.ATTR_INPUT_SOURCE)


class FanSpeedCapability(StateModeCapability, ABC):
    """Base capability to control a device fan speed."""

    instance = ModeCapabilityInstance.FAN_SPEED


@STATE_CAPABILITIES_REGISTRY.register
class FanSpeedCapabilityClimate(FanSpeedCapability):
    """Capability to control the fan speed of a climate device."""

    _modes_map_default = {
        ModeCapabilityMode.AUTO: [
            climate.const.FAN_AUTO,
            climate.const.FAN_ON,
            const.SMARTTHINQ_FAN_PRESET_NATURE,
        ],
        ModeCapabilityMode.QUIET: [
            climate.const.FAN_OFF,
            climate.const.FAN_DIFFUSE,
            const.FAN_SPEED_QUIET,
        ],
        ModeCapabilityMode.MIN: [
            const.TION_FAN_SPEED_1,
            const.FAN_SPEED_LOW_MID,
        ],
        ModeCapabilityMode.LOW: [
            climate.const.FAN_LOW,
            const.FAN_SPEED_MIN,
            const.TION_FAN_SPEED_2,
        ],
        ModeCapabilityMode.MEDIUM: [
            climate.const.FAN_MEDIUM,
            climate.const.FAN_MIDDLE,
            const.FAN_SPEED_MID,
            const.TION_FAN_SPEED_3,
        ],
        ModeCapabilityMode.HIGH: [
            climate.const.FAN_HIGH,
            const.FAN_SPEED_MAX,
            const.TION_FAN_SPEED_4,
        ],
        ModeCapabilityMode.TURBO: [
            climate.const.FAN_FOCUS,
            const.FAN_SPEED_HIGHEST,
            const.TION_FAN_SPEED_5,
        ],
        ModeCapabilityMode.MAX: [
            const.TION_FAN_SPEED_6,
            const.FAN_SPEED_MID_HIGH,
        ],
    }

    @property
    def supported(self) -> bool:
        """Test if the capability is supported."""
        if self.state.domain == climate.DOMAIN and self._state_features & climate.ClimateEntityFeature.FAN_MODE:
            return super().supported

        return False

    async def set_instance_state(self, context: Context, state: ModeCapabilityInstanceActionState) -> None:
        """Change the capability state."""
        await self._hass.services.async_call(
            climate.DOMAIN,
            climate.SERVICE_SET_FAN_MODE,
            {
                ATTR_ENTITY_ID: self.state.entity_id,
                climate.ATTR_FAN_MODE: self.get_ha_mode_by_yandex_mode(state.value),
            },
            blocking=True,
            context=context,
        )

    @property
    def _ha_modes(self) -> Iterable[Any]:
        """Returns list of HA modes."""
        modes = self.state.attributes.get(climate.ATTR_FAN_MODES, []) or []

        # esphome default state for some devices
        if self._ha_value == climate.const.FAN_ON and climate.const.FAN_ON not in modes:
            modes.append(climate.const.FAN_ON)

        return modes

    @property
    def _ha_value(self) -> Any:
        """Return the current unmapped capability value."""
        return self.state.attributes.get(climate.ATTR_FAN_MODE)


@STATE_CAPABILITIES_REGISTRY.register
class FanSpeedCapabilityFanViaPreset(FanSpeedCapability):
    """Capability to control the fan speed of a fan device via preset."""

    _modes_map_default = {
        ModeCapabilityMode.AUTO: [
            climate.const.FAN_AUTO,
            climate.const.FAN_ON,
        ],
        ModeCapabilityMode.ECO: [
            const.XIAOMI_AIRPURIFIER_PRESET_IDLE,
        ],
        ModeCapabilityMode.QUIET: [
            const.FAN_SPEED_OFF,
            const.XIAOMI_AIRPURIFIER_PRESET_SILENT,
            const.XIAOMI_FAN_PRESET_LEVEL_1,
        ],
        ModeCapabilityMode.LOW: [
            const.FAN_SPEED_LOW,
            const.FAN_SPEED_MIN,
            const.XIAOMI_FAN_PRESET_LEVEL_2,
        ],
        ModeCapabilityMode.MEDIUM: [
            const.FAN_SPEED_MEDIUM,
            const.XIAOMI_HUMIDIFIER_PRESET_MID,
            const.XIAOMI_FAN_PRESET_LEVEL_3,
        ],
        ModeCapabilityMode.NORMAL: [
            const.XIAOMI_AIRPURIFIER_PRESET_FAVORITE,
        ],
        ModeCapabilityMode.HIGH: [
            const.FAN_SPEED_HIGH,
            const.XIAOMI_FAN_PRESET_LEVEL_4,
        ],
        ModeCapabilityMode.TURBO: [
            const.FAN_SPEED_MAX,
            const.XIAOMI_AIRPURIFIER_PRESET_STRONG,
            const.XIAOMI_FAN_PRESET_LEVEL_5,
        ],
    }

    @property
    def supported(self) -> bool:
        """Test if the capability is supported."""
        if self.state.domain == fan.DOMAIN:
            if self._state_features & fan.FanEntityFeature.PRESET_MODE:
                if (
                    self._state_features & fan.FanEntityFeature.SET_SPEED
                    and fan.ATTR_PERCENTAGE_STEP in self.state.attributes
                ):
                    return False

                return super().supported

        return False

    async def set_instance_state(self, context: Context, state: ModeCapabilityInstanceActionState) -> None:
        """Change the capability state."""
        await self._hass.services.async_call(
            fan.DOMAIN,
            fan.SERVICE_SET_PRESET_MODE,
            {
                ATTR_ENTITY_ID: self.state.entity_id,
                fan.ATTR_PRESET_MODE: self.get_ha_mode_by_yandex_mode(state.value),
            },
            blocking=True,
            context=context,
        )

    @property
    def _ha_modes(self) -> Iterable[Any]:
        """Returns list of HA modes."""
        return self.state.attributes.get(fan.ATTR_PRESET_MODES, []) or []

    @property
    def _ha_value(self) -> Any:
        """Return the current unmapped capability value."""
        return self.state.attributes.get(fan.ATTR_PRESET_MODE)


@STATE_CAPABILITIES_REGISTRY.register
class FanSpeedCapabilityFanViaPercentage(FanSpeedCapability):
    """Capability to control the fan speed in percents of a fan device."""

    @property
    def supported(self) -> bool:
        """Test if the capability is supported."""
        if self.state.domain == fan.DOMAIN:
            if (
                self._state_features & fan.FanEntityFeature.SET_SPEED
                and fan.ATTR_PERCENTAGE_STEP in self.state.attributes
            ):
                return super().supported

        return False

    @property
    def supported_yandex_modes(self) -> list[ModeCapabilityMode]:
        """Returns a list of supported Yandex modes."""
        return [ModeCapabilityMode(m) for m in self.supported_ha_modes]

    def get_value(self) -> ModeCapabilityMode | None:
        """Return the current capability value."""
        if not self._ha_value:
            return None

        value = int(self._ha_value)
        if self.modes_map:
            for yandex_mode, values in self.modes_map.items():
                for str_value in values:
                    if value == self._convert_mapping_speed_value(str_value):
                        return yandex_mode

            return None

        return ModeCapabilityMode(percentage_to_ordered_list_item(self.supported_ha_modes, value))

    async def set_instance_state(self, context: Context, state: ModeCapabilityInstanceActionState) -> None:
        """Change the capability state."""
        if self.modes_map:
            ha_modes = self.modes_map.get(state.value)
            if not ha_modes:
                raise APIError(
                    ResponseCode.INVALID_VALUE,
                    f"Unsupported mode '{state.value}' for {self}, see https://docs.yaha-cloud.ru/master/config/modes/",
                )

            ha_mode = self._convert_mapping_speed_value(ha_modes[0])
        else:
            ha_mode = ordered_list_item_to_percentage(self.supported_ha_modes, state.value)

        await self._hass.services.async_call(
            fan.DOMAIN,
            fan.SERVICE_SET_PERCENTAGE,
            {ATTR_ENTITY_ID: self.state.entity_id, fan.ATTR_PERCENTAGE: ha_mode},
            blocking=True,
            context=context,
        )

    @property
    def _ha_modes(self) -> Iterable[Any]:
        """Returns list of HA modes."""
        if self.modes_map:
            return self.modes_map.keys()

        percentage_step = self.state.attributes.get(fan.ATTR_PERCENTAGE_STEP, 100)
        speed_count = math.ceil(100 / percentage_step)
        if speed_count == 1:
            return []

        modes = [ModeCapabilityMode.LOW, ModeCapabilityMode.HIGH]
        if speed_count >= 3:
            modes.insert(modes.index(ModeCapabilityMode.HIGH), ModeCapabilityMode.MEDIUM)
        if speed_count >= 4:
            modes.insert(modes.index(ModeCapabilityMode.MEDIUM), ModeCapabilityMode.NORMAL)
        if speed_count >= 5:
            modes.insert(0, ModeCapabilityMode.ECO)
        if speed_count >= 6:
            modes.insert(modes.index(ModeCapabilityMode.LOW), ModeCapabilityMode.QUIET)
        if speed_count >= 7:
            modes.append(ModeCapabilityMode.TURBO)

        return modes

    @property
    def _ha_value(self) -> Any:
        """Return the current unmapped capability value."""
        return self.state.attributes.get(fan.ATTR_PERCENTAGE)

    def _convert_mapping_speed_value(self, value: str) -> int:
        try:
            return int(value.replace("%", ""))
        except ValueError:
            raise APIError(ResponseCode.INVALID_VALUE, f"Unsupported speed value '{value}' for {self}")


@STATE_CAPABILITIES_REGISTRY.register
class CleanupModeCapability(StateModeCapability):
    """Capability to control the program of a vacuum."""

    instance = ModeCapabilityInstance.CLEANUP_MODE

    _modes_map_default = {
        ModeCapabilityMode.ECO: [const.CLEANUP_MODE_OFF],
        ModeCapabilityMode.AUTO: ["auto", "automatic", "102", const.CLEANUP_MODE_BALANCED],
        ModeCapabilityMode.TURBO: [const.CLEANUP_MODE_TURBO, "high", "performance", "104", "full speed", "max+"],
        ModeCapabilityMode.MIN: ["min", "mop"],
        ModeCapabilityMode.LOW: ["gentle"],
        ModeCapabilityMode.MAX: [const.CLEANUP_MODE_MAX, "strong"],
        ModeCapabilityMode.FAST: [const.CLEANUP_MODE_MAX_PLUS],
        ModeCapabilityMode.EXPRESS: ["express", "105"],
        ModeCapabilityMode.MEDIUM: ["medium", "middle"],
        ModeCapabilityMode.NORMAL: ["normal", "standard", "basic", "103"],
        ModeCapabilityMode.QUIET: ["quiet", "low", "min", const.CLEANUP_MODE_SILENT, "eco", "101", "slient"],
        ModeCapabilityMode.SMART: [const.CLEANUP_MODE_MAX_PLUS],
    }

    @property
    def supported(self) -> bool:
        """Test if the capability is supported."""
        if self.state.domain == vacuum.DOMAIN and self._state_features & vacuum.VacuumEntityFeature.FAN_SPEED:
            return super().supported

        return False

    async def set_instance_state(self, context: Context, state: ModeCapabilityInstanceActionState) -> None:
        """Change the capability state."""
        await self._hass.services.async_call(
            vacuum.DOMAIN,
            vacuum.SERVICE_SET_FAN_SPEED,
            {
                ATTR_ENTITY_ID: self.state.entity_id,
                vacuum.ATTR_FAN_SPEED: self.get_ha_mode_by_yandex_mode(state.value),
            },
            blocking=True,
            context=context,
        )

    @property
    def _ha_modes(self) -> Iterable[Any]:
        """Returns list of HA modes."""
        return self.state.attributes.get(vacuum.ATTR_FAN_SPEED_LIST, []) or []

    @property
    def _ha_value(self) -> Any:
        """Return the current unmapped capability value."""
        return self.state.attributes.get(vacuum.ATTR_FAN_SPEED)
