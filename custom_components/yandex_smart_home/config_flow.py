from homeassistant.config_entries import ConfigFlow
from homeassistant.helpers.reload import async_integration_yaml_config

from . import DOMAIN

import logging
_LOGGER = logging.getLogger(__name__)


class ConfigFlowHandler(ConfigFlow, domain=DOMAIN):
    # noinspection PyUnusedLocal
    async def async_step_import(self, user_input=None):
        return await self.async_step_user()

    async def async_step_user(self, user_input=None):
        if self._async_current_entries():
            return self.async_abort(reason='single_instance_allowed')

        yaml_config = await async_integration_yaml_config(self.hass, DOMAIN)
        if not yaml_config or DOMAIN not in yaml_config:
            return self.async_abort(reason='missing_configuration')

        return self.async_create_entry(title='Yandex Smart Home', data={})
