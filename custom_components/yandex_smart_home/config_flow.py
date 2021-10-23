from __future__ import annotations

import logging

from homeassistant import data_entry_flow
from homeassistant.config_entries import ConfigFlow
from homeassistant.helpers.typing import ConfigType

from . import DOMAIN

_LOGGER = logging.getLogger(__name__)


class ConfigFlowHandler(ConfigFlow, domain=DOMAIN):
    async def async_step_user(self, user_input: ConfigType | None = None) -> data_entry_flow.FlowResult:
        if self._async_current_entries():
            return self.async_abort(reason='single_instance_allowed')

        return self.async_create_entry(title='Yandex Smart Home', data={})
