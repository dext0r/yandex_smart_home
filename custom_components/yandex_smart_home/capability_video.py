from __future__ import annotations

import logging
from typing import Any

from homeassistant.components import camera
from homeassistant.const import ATTR_SUPPORTED_FEATURES
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import network

from .capability import PREFIX_CAPABILITIES, AbstractCapability, register_capability
from .const import CLOUD_BASE_URL, ERR_NOT_SUPPORTED_IN_CURRENT_MODE
from .error import SmartHomeError
from .helpers import Config, RequestData

_LOGGER = logging.getLogger(__name__)

CAPABILITIES_VIDEO_STREAM = PREFIX_CAPABILITIES + 'video_stream'
VIDEO_STREAM_FORMAT = 'hls'


@register_capability
class VideoStreamCapability(AbstractCapability):

    type = CAPABILITIES_VIDEO_STREAM
    instance = 'get_stream'
    retrievable = False

    def __init__(self, hass: HomeAssistant, config: Config, state: State):
        super().__init__(hass, config, state)

        self._config = config
        self.reportable = False

    def parameters(self) -> dict[str, Any]:
        return {
            'protocol': VIDEO_STREAM_FORMAT
        }

    def supported(self) -> bool:
        if self.state.domain != camera.DOMAIN:
            return False

        features = self.state.attributes.get(ATTR_SUPPORTED_FEATURES, 0)
        return bool(features & camera.SUPPORT_STREAM) and self._config.beta

    def get_value(self) -> float | str | bool | None:
        return None

    async def set_state(self, data: RequestData, state: dict[str, Any]) -> dict[str, Any] | None:
        stream_source = await camera.async_request_stream(self.hass, self.state.entity_id, fmt=VIDEO_STREAM_FORMAT)

        if self._config.is_cloud_connection:
            external_url = f'{CLOUD_BASE_URL}/api/proxy/{self._config.cloud_instance_id}'
        else:
            try:
                external_url = network.get_url(self.hass, allow_internal=False)
            except network.NoURLAvailableError:
                raise SmartHomeError(
                    ERR_NOT_SUPPORTED_IN_CURRENT_MODE,
                    'Unable to get Home Assistant external URL. Have you set external URLs in Configuration -> General?'
                )

        return {
            'stream_url': f'{external_url}{stream_source}'
        }
