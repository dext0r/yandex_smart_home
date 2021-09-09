"""Implement the Yandex Smart Home on_off capability."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components import (
    climate,
    cover,
    fan,
    group,
    humidifier,
    input_boolean,
    light,
    lock,
    media_player,
    scene,
    script,
    switch,
    vacuum,
    water_heater,
)
from homeassistant.components.water_heater import SERVICE_SET_OPERATION_MODE, STATE_ELECTRIC
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_SUPPORTED_FEATURES,
    SERVICE_CLOSE_COVER,
    SERVICE_LOCK,
    SERVICE_OPEN_COVER,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    SERVICE_UNLOCK,
    STATE_OFF,
    STATE_ON,
)
from homeassistant.core import DOMAIN as HA_DOMAIN, HomeAssistant, State
from homeassistant.helpers.service import async_call_from_config

from . import const
from .capability import PREFIX_CAPABILITIES, AbstractCapability, register_capability
from .helpers import Config, RequestData

_LOGGER = logging.getLogger(__name__)

CAPABILITIES_ONOFF = PREFIX_CAPABILITIES + 'on_off'


@register_capability
class OnOffCapability(AbstractCapability):
    """On_off to offer basic on and off functionality.

    https://yandex.ru/dev/dialogs/alice/doc/smart-home/concepts/on_off-docpage/
    """

    type = CAPABILITIES_ONOFF
    instance = const.ON_OFF_INSTANCE_ON
    water_heater_operations = {
        STATE_ON: [STATE_ON, 'On', 'ON', STATE_ELECTRIC],
        STATE_OFF: [STATE_OFF, 'Off', 'OFF'],
    }

    def __init__(self, hass: HomeAssistant, config: Config, state: State):
        super().__init__(hass, config, state)
        self.retrievable = state.domain != scene.DOMAIN and state.domain != \
            script.DOMAIN

        if self.state.domain == cover.DOMAIN:
            if not self.state.attributes.get(ATTR_SUPPORTED_FEATURES, 0) & cover.SUPPORT_SET_POSITION:
                self.retrievable = False

    def get_water_heater_operation(self, required_mode, operations_list):
        for operation in self.water_heater_operations[required_mode]:
            if operation in operations_list:
                return operation

        return None

    def supported(self) -> bool:
        """Test if capability is supported."""
        features = self.state.attributes.get(ATTR_SUPPORTED_FEATURES, 0)

        if const.CONF_TURN_ON in self.entity_config:
            return True

        if self.state.domain == media_player.DOMAIN:
            return features & media_player.SUPPORT_TURN_ON and features & media_player.SUPPORT_TURN_OFF

        if self.state.domain == vacuum.DOMAIN:
            return (features & vacuum.SUPPORT_START and (
                        features & vacuum.SUPPORT_RETURN_HOME or features & vacuum.SUPPORT_STOP)) or (
                               features & vacuum.SUPPORT_TURN_ON and features & vacuum.SUPPORT_TURN_OFF)

        if self.state.domain == water_heater.DOMAIN and features & water_heater.SUPPORT_OPERATION_MODE:
            operation_list = self.state.attributes.get(water_heater.ATTR_OPERATION_LIST)
            if self.get_water_heater_operation(STATE_ON, operation_list) is None:
                return False
            if self.get_water_heater_operation(STATE_OFF, operation_list) is None:
                return False
            return True

        return self.state.domain in (
            cover.DOMAIN,
            group.DOMAIN,
            input_boolean.DOMAIN,
            switch.DOMAIN,
            fan.DOMAIN,
            light.DOMAIN,
            climate.DOMAIN,
            scene.DOMAIN,
            script.DOMAIN,
            lock.DOMAIN,
            humidifier.DOMAIN,
        )

    def parameters(self) -> dict[str, Any] | None:
        """Return parameters for a devices request."""
        if self.state.domain == cover.DOMAIN:
            features = self.state.attributes.get(ATTR_SUPPORTED_FEATURES, 0)
            if not features & cover.SUPPORT_SET_POSITION:
                return {'split': True}

        return None

    def get_value(self) -> str | None:
        """Return the state value of this capability for this entity."""
        if self.state.domain == cover.DOMAIN:
            return self.state.state == cover.STATE_OPEN
        elif self.state.domain == vacuum.DOMAIN:
            return self.state.state == STATE_ON or self.state.state == \
                   vacuum.STATE_CLEANING
        elif self.state.domain == climate.DOMAIN:
            return self.state.state != climate.HVAC_MODE_OFF
        elif self.state.domain == lock.DOMAIN:
            return self.state.state == lock.STATE_UNLOCKED
        elif self.state.domain == water_heater.DOMAIN:
            operation_mode = self.state.attributes.get(water_heater.ATTR_OPERATION_MODE)
            operation_list = self.state.attributes.get(water_heater.ATTR_OPERATION_LIST)
            return operation_mode != self.get_water_heater_operation(STATE_OFF, operation_list)
        else:
            return self.state.state != STATE_OFF

    async def set_state(self, data: RequestData, state: dict[str, Any]):
        """Set device state."""
        for key, call in ((const.CONF_TURN_ON, state['value']), (const.CONF_TURN_OFF, not state['value'])):
            if key in self.entity_config and call:
                return await async_call_from_config(
                    self.hass,
                    self.entity_config[key],
                    blocking=True,
                    context=data.context
                )

        domain = service_domain = self.state.domain
        service_data = {
            ATTR_ENTITY_ID: self.state.entity_id
        }
        if domain == group.DOMAIN:
            service_domain = HA_DOMAIN
            service = SERVICE_TURN_ON if state['value'] else SERVICE_TURN_OFF
        elif domain == cover.DOMAIN:
            service = SERVICE_OPEN_COVER if state['value'] else \
                SERVICE_CLOSE_COVER
        elif domain == vacuum.DOMAIN:
            features = self.state.attributes.get(ATTR_SUPPORTED_FEATURES)
            if state['value']:
                if features & vacuum.SUPPORT_START:
                    service = vacuum.SERVICE_START
                else:
                    service = SERVICE_TURN_ON
            else:
                if features & vacuum.SUPPORT_RETURN_HOME:
                    service = vacuum.SERVICE_RETURN_TO_BASE
                elif features & vacuum.SUPPORT_STOP:
                    service = vacuum.SERVICE_STOP
                else:
                    service = SERVICE_TURN_OFF
        elif self.state.domain in (scene.DOMAIN, script.DOMAIN):
            service = SERVICE_TURN_ON
        elif self.state.domain == lock.DOMAIN:
            service = SERVICE_UNLOCK if state['value'] else \
                SERVICE_LOCK
        elif self.state.domain == water_heater.DOMAIN:
            operation_list = self.state.attributes.get(water_heater.ATTR_OPERATION_LIST)
            service = SERVICE_SET_OPERATION_MODE
            if state['value']:
                service_data[water_heater.ATTR_OPERATION_MODE] = \
                    self.get_water_heater_operation(STATE_ON, operation_list)
            else:
                service_data[water_heater.ATTR_OPERATION_MODE] = \
                    self.get_water_heater_operation(STATE_OFF, operation_list)
        else:
            service = SERVICE_TURN_ON if state['value'] else SERVICE_TURN_OFF

        if self.state.domain == climate.DOMAIN and state['value']:
            hvac_modes = self.state.attributes.get(climate.ATTR_HVAC_MODES)
            for mode in (climate.const.HVAC_MODE_HEAT_COOL,
                         climate.const.HVAC_MODE_AUTO):
                if mode not in hvac_modes:
                    continue

                service_data[climate.ATTR_HVAC_MODE] = mode
                service = climate.SERVICE_SET_HVAC_MODE
                break

        await self.hass.services.async_call(service_domain, service, service_data,
                                            blocking=self.state.domain != script.DOMAIN, context=data.context)
