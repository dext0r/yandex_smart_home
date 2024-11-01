"""Implement the Yandex Smart Home on_off capability."""
from __future__ import annotations

from abc import ABC, abstractmethod
import logging
from typing import Any

from homeassistant.components import (
    automation,
    button,
    climate,
    cover,
    fan,
    group,
    humidifier,
    input_boolean,
    input_button,
    light,
    lock,
    media_player,
    remote,
    scene,
    script,
    switch,
    vacuum,
    water_heater,
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_SUPPORTED_FEATURES,
    MAJOR_VERSION,
    MINOR_VERSION,
    SERVICE_CLOSE_COVER,
    SERVICE_LOCK,
    SERVICE_OPEN_COVER,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    SERVICE_UNLOCK,
    STATE_OFF,
    STATE_ON,
    STATE_OPEN,
)
from homeassistant.core import DOMAIN as HA_DOMAIN
from homeassistant.exceptions import ServiceNotFound
from homeassistant.helpers.service import async_call_from_config

from . import const
from .capability import PREFIX_CAPABILITIES, AbstractCapability, register_capability
from .const import ERR_NOT_SUPPORTED_IN_CURRENT_MODE
from .error import SmartHomeError
from .helpers import RequestData

_LOGGER = logging.getLogger(__name__)

CAPABILITIES_ONOFF = PREFIX_CAPABILITIES + 'on_off'


class OnOffCapability(AbstractCapability, ABC):
    """On_off to offer basic on and off functionality.

    https://yandex.ru/dev/dialogs/alice/doc/smart-home/concepts/on_off-docpage/
    """

    type = CAPABILITIES_ONOFF
    instance = const.ON_OFF_INSTANCE_ON

    @property
    def retrievable(self) -> bool:
        if self.entity_config.get(const.CONF_STATE_UNKNOWN):
            return False

        return True

    def parameters(self) -> dict[str, Any] | None:
        """Return parameters for a devices request."""
        if not self.retrievable:
            return {'split': True}

        return None

    def get_value(self) -> bool | None:
        return self.state.state != STATE_OFF

    async def set_state(self, data: RequestData, state: dict[str, Any]):
        for key, call in ((const.CONF_TURN_ON, state['value']), (const.CONF_TURN_OFF, not state['value'])):
            if key in self.entity_config and call:
                return await async_call_from_config(
                    self.hass,
                    self.entity_config[key],
                    blocking=True,
                    context=data.context
                )

        await self._set_state(data, state)

    @abstractmethod
    async def _set_state(self, data: RequestData, state: dict[str, Any]):
        pass


class OnlyOnCapability(OnOffCapability, ABC):
    @property
    def retrievable(self) -> bool:
        return False

    def parameters(self) -> dict[str, Any] | None:
        return None


@register_capability
class OnOffCapabilityBasic(OnOffCapability):
    def supported(self) -> bool:
        return self.state.domain in (light.DOMAIN, fan.DOMAIN, switch.DOMAIN, humidifier.DOMAIN, input_boolean.DOMAIN)

    async def _set_state(self, data: RequestData, state: dict[str, Any]):
        if state['value']:
            service = SERVICE_TURN_ON
        else:
            service = SERVICE_TURN_OFF

        await self.hass.services.async_call(
            self.state.domain,
            service, {
                ATTR_ENTITY_ID: self.state.entity_id
            },
            blocking=True,
            context=data.context
        )


@register_capability
class OnOffCapabilityAutomation(OnOffCapability):
    def get_value(self) -> bool:
        return self.state.state == STATE_ON

    def supported(self) -> bool:
        return self.state.domain == automation.DOMAIN

    async def _set_state(self, data: RequestData, state: dict[str, Any]):
        if state['value']:
            service = SERVICE_TURN_ON
        else:
            service = SERVICE_TURN_OFF

        await self.hass.services.async_call(
            automation.DOMAIN,
            service, {
                ATTR_ENTITY_ID: self.state.entity_id
            },
            blocking=True,
            context=data.context
        )


@register_capability
class OnOffCapabilityGroup(OnOffCapability):
    def supported(self) -> bool:
        return self.state.domain in group.DOMAIN

    async def _set_state(self, data: RequestData, state: dict[str, Any]):
        if state['value']:
            service = SERVICE_TURN_ON
        else:
            service = SERVICE_TURN_OFF

        await self.hass.services.async_call(
            HA_DOMAIN,
            service, {
                ATTR_ENTITY_ID: self.state.entity_id
            },
            blocking=True,
            context=data.context
        )


@register_capability
class OnOffCapabilityScript(OnlyOnCapability):
    def get_value(self) -> bool | None:
        return None

    def supported(self) -> bool:
        return self.state.domain in (scene.DOMAIN, script.DOMAIN)

    async def _set_state(self, data: RequestData, state: dict[str, Any]):
        await self.hass.services.async_call(
            self.state.domain,
            SERVICE_TURN_ON, {
                ATTR_ENTITY_ID: self.state.entity_id
            },
            blocking=self.state.domain != script.DOMAIN,
            context=data.context
        )


@register_capability
class OnOffCapabilityButton(OnlyOnCapability):
    def get_value(self) -> bool | None:
        return None

    def supported(self) -> bool:
        return self.state.domain == button.DOMAIN

    async def _set_state(self, data: RequestData, state: dict[str, Any]):
        await self.hass.services.async_call(
            self.state.domain,
            button.SERVICE_PRESS, {
                ATTR_ENTITY_ID: self.state.entity_id
            },
            blocking=True,
            context=data.context
        )


@register_capability
class OnOffCapabilityInputButton(OnlyOnCapability):
    def get_value(self) -> bool | None:
        return None

    def supported(self) -> bool:
        return self.state.domain == input_button.DOMAIN

    async def _set_state(self, data: RequestData, state: dict[str, Any]):
        await self.hass.services.async_call(
            self.state.domain,
            input_button.SERVICE_PRESS, {
                ATTR_ENTITY_ID: self.state.entity_id
            },
            blocking=True,
            context=data.context
        )


@register_capability
class OnOffCapabilityLock(OnOffCapability):
    def get_value(self) -> bool:
        if (MAJOR_VERSION == 2024 and MINOR_VERSION >= 10) or MAJOR_VERSION >= 2025:
            return self.state.state == lock.LockState.UNLOCKED
        else:
            return self.state.state == lock.STATE_UNLOCKED

    def supported(self) -> bool:
        return self.state.domain == lock.DOMAIN

    async def _set_state(self, data: RequestData, state: dict[str, Any]):
        if state['value']:
            service = SERVICE_UNLOCK
        else:
            service = SERVICE_LOCK

        await self.hass.services.async_call(
            lock.DOMAIN,
            service, {
                ATTR_ENTITY_ID: self.state.entity_id
            },
            blocking=True,
            context=data.context
        )


@register_capability
class OnOffCapabilityCover(OnOffCapability):
    def get_value(self) -> bool:
        return self.state.state == cover.STATE_OPEN

    def supported(self) -> bool:
        return self.state.domain == cover.DOMAIN

    async def _set_state(self, data: RequestData, state: dict[str, Any]):
        if state['value']:
            service = SERVICE_OPEN_COVER
        else:
            service = SERVICE_CLOSE_COVER

        await self.hass.services.async_call(
            cover.DOMAIN,
            service, {
                ATTR_ENTITY_ID: self.state.entity_id
            },
            blocking=True,
            context=data.context
        )


if MAJOR_VERSION >= 2024:
    from homeassistant.components import valve
    from homeassistant.const import SERVICE_CLOSE_VALVE, SERVICE_OPEN_VALVE

    @register_capability
    class OnOffCapabilityValve(OnOffCapability):
        def get_value(self) -> bool:
            return self.state.state == STATE_OPEN

        def supported(self) -> bool:
            return self.state.domain == valve.DOMAIN

        async def _set_state(self, data: RequestData, state: dict[str, Any]):
            if state['value']:
                service = SERVICE_OPEN_VALVE
            else:
                service = SERVICE_CLOSE_VALVE

            await self.hass.services.async_call(
                valve.DOMAIN,
                service, {
                    ATTR_ENTITY_ID: self.state.entity_id
                },
                blocking=True,
                context=data.context
            )


@register_capability
class OnOffCapabilityRemote(OnOffCapability):
    @property
    def retrievable(self) -> bool:
        return False

    def get_value(self) -> None:
        return None

    def supported(self) -> bool:
        return self.state.domain == remote.DOMAIN

    async def _set_state(self, data: RequestData, state: dict[str, Any]):
        if state['value']:
            service = SERVICE_TURN_ON
        else:
            service = SERVICE_TURN_OFF

        await self.hass.services.async_call(
            remote.DOMAIN,
            service, {
                ATTR_ENTITY_ID: self.state.entity_id
            },
            blocking=False,
            context=data.context
        )


@register_capability
class OnOffCapabilityMediaPlayer(OnOffCapability):
    def supported(self) -> bool:
        if self.state.domain == media_player.DOMAIN:
            features = self.state.attributes.get(ATTR_SUPPORTED_FEATURES, 0)

            if const.CONF_TURN_ON in self.entity_config or const.CONF_TURN_OFF in self.entity_config:
                return True

            if const.MEDIA_PLAYER_FEATURE_TURN_ON_OFF in self.entity_config.get(const.CONF_FEATURES, []):
                return True

            return features & media_player.MediaPlayerEntityFeature.TURN_ON or \
                features & media_player.MediaPlayerEntityFeature.TURN_OFF

        return False

    async def _set_state(self, data: RequestData, state: dict[str, Any]):
        if state['value']:
            service = SERVICE_TURN_ON
        else:
            service = SERVICE_TURN_OFF

        await self.hass.services.async_call(
            media_player.DOMAIN,
            service, {
                ATTR_ENTITY_ID: self.state.entity_id
            },
            blocking=True,
            context=data.context
        )


@register_capability
class OnOffCapabilityVacuum(OnOffCapability):
    def get_value(self) -> bool | None:
        return self.state.state in [STATE_ON, vacuum.STATE_CLEANING]

    def supported(self) -> bool:
        if self.state.domain != vacuum.DOMAIN:
            return False

        if const.CONF_TURN_ON in self.entity_config:
            return True

        features = self.state.attributes.get(ATTR_SUPPORTED_FEATURES, 0)

        if features & vacuum.VacuumEntityFeature.TURN_ON and features & vacuum.VacuumEntityFeature.TURN_OFF:
            return True

        if features & vacuum.VacuumEntityFeature.START:
            if features & vacuum.VacuumEntityFeature.RETURN_HOME or features & vacuum.VacuumEntityFeature.STOP:
                return True

        return False

    async def _set_state(self, data: RequestData, state: dict[str, Any]):
        features = self.state.attributes.get(ATTR_SUPPORTED_FEATURES)

        if state['value']:
            if features & vacuum.VacuumEntityFeature.START:
                service = vacuum.SERVICE_START
            else:
                service = SERVICE_TURN_ON
        else:
            if features & vacuum.VacuumEntityFeature.RETURN_HOME:
                service = vacuum.SERVICE_RETURN_TO_BASE
            elif features & vacuum.VacuumEntityFeature.STOP:
                service = vacuum.SERVICE_STOP
            else:
                service = SERVICE_TURN_OFF

        await self.hass.services.async_call(
            vacuum.DOMAIN,
            service, {
                ATTR_ENTITY_ID: self.state.entity_id
            },
            blocking=True,
            context=data.context
        )


@register_capability
class OnOffCapabilityClimate(OnOffCapability):
    def get_value(self) -> bool | None:
        return self.state.state != climate.HVACMode.OFF

    def supported(self) -> bool:
        return self.state.domain == climate.DOMAIN

    async def _set_state(self, data: RequestData, state: dict[str, Any]):
        service_data = {
            ATTR_ENTITY_ID: self.state.entity_id
        }

        if state['value']:
            service = SERVICE_TURN_ON

            hvac_modes = self.state.attributes.get(climate.ATTR_HVAC_MODES)
            for mode in (climate.HVACMode.HEAT_COOL,
                         climate.HVACMode.AUTO):
                if mode not in hvac_modes:
                    continue

                service_data[climate.ATTR_HVAC_MODE] = mode
                service = climate.SERVICE_SET_HVAC_MODE
                break
        else:
            service = SERVICE_TURN_OFF

        await self.hass.services.async_call(
            climate.DOMAIN,
            service,
            service_data,
            blocking=True,
            context=data.context
        )


@register_capability
class OnOffCapabilityWaterHeater(OnOffCapability):
    water_heater_operations = {
        STATE_ON: [STATE_ON, 'On', 'ON', water_heater.STATE_ELECTRIC, const.SKYKETTLE_MODE_BOIL],
        STATE_OFF: [STATE_OFF, 'Off', 'OFF'],
    }

    def get_value(self) -> bool | None:
        return self.state.state.lower() != water_heater.STATE_OFF

    def get_water_heater_operation(self, required_mode: str, operations_list: list[str]) -> str | None:
        for operation in self.water_heater_operations[required_mode]:
            if operation in operations_list:
                return operation

        return None

    def supported(self) -> bool:
        return self.state.domain == water_heater.DOMAIN

    async def _set_state(self, data: RequestData, state: dict[str, Any]):
        if state['value']:
            service = water_heater.SERVICE_TURN_ON
        else:
            service = water_heater.SERVICE_TURN_OFF

        try:
            await self.hass.services.async_call(
                water_heater.DOMAIN,
                service, {
                    ATTR_ENTITY_ID: self.state.entity_id,
                },
                blocking=True,
                context=data.context
            )

            return
        except (AttributeError, ServiceNotFound):
            # turn_on/turn_off is not supported
            pass

        operation_list = self.state.attributes.get(water_heater.ATTR_OPERATION_LIST)

        if state['value']:
            mode = self.get_water_heater_operation(STATE_ON, operation_list)
        else:
            mode = self.get_water_heater_operation(STATE_OFF, operation_list)

        if not mode:
            target_state_text = 'on' if state['value'] else 'off'
            raise SmartHomeError(
                ERR_NOT_SUPPORTED_IN_CURRENT_MODE,
                f'Unable to determine operation mode for {target_state_text} state'
            )

        await self.hass.services.async_call(
            water_heater.DOMAIN,
            water_heater.SERVICE_SET_OPERATION_MODE, {
                ATTR_ENTITY_ID: self.state.entity_id,
                water_heater.ATTR_OPERATION_MODE: mode
            },
            blocking=True,
            context=data.context
        )
