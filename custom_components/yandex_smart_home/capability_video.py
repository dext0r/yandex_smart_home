from __future__ import annotations

import logging
from typing import Any

from homeassistant.components import camera
from homeassistant.components.camera import StreamType, _get_camera_from_entity_id
from homeassistant.components.stream import Stream
from homeassistant.const import ATTR_SUPPORTED_FEATURES
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import network
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .capability import PREFIX_CAPABILITIES, AbstractCapability, register_capability
from .cloud_stream import CloudStream
from .const import CLOUD_STREAMS, DOMAIN, ERR_NOT_SUPPORTED_IN_CURRENT_MODE, VIDEO_STREAM_INSTANCE_GET_STREAM
from .error import SmartHomeError
from .helpers import Config, RequestData

_LOGGER = logging.getLogger(__name__)

CAPABILITIES_VIDEO_STREAM = PREFIX_CAPABILITIES + 'video_stream'


@register_capability
class VideoStreamCapability(AbstractCapability):

    type = CAPABILITIES_VIDEO_STREAM
    instance = VIDEO_STREAM_INSTANCE_GET_STREAM
    retrievable = False

    def __init__(self, hass: HomeAssistant, config: Config, state: State):
        super().__init__(hass, config, state)

        self._config = config
        self.reportable = False

    def parameters(self) -> dict[str, Any]:
        return {
            'protocols': [str(StreamType.HLS)]
        }

    def supported(self) -> bool:
        if self.state.domain != camera.DOMAIN:
            return False

        features = self.state.attributes.get(ATTR_SUPPORTED_FEATURES, 0)
        return features & camera.CameraEntityFeature.STREAM

    def get_value(self) -> float | str | bool | None:
        return None

    async def set_state(self, data: RequestData, state: dict[str, Any]) -> dict[str, Any] | None:
        entity_id = self.state.entity_id
        stream = await self._async_request_stream(entity_id)

        if self._config.use_cloud_stream:
            cloud_stream = self.hass.data[DOMAIN][CLOUD_STREAMS].get(entity_id)
            if not cloud_stream:
                cloud_stream = CloudStream(self.hass, stream, async_get_clientsession(self.hass))
                self.hass.data[DOMAIN][CLOUD_STREAMS][entity_id] = cloud_stream

            await cloud_stream.start()
            stream_url = cloud_stream.stream_url
        else:
            try:
                external_url = network.get_url(self.hass, allow_internal=False)
            except network.NoURLAvailableError:
                raise SmartHomeError(
                    ERR_NOT_SUPPORTED_IN_CURRENT_MODE,
                    'Unable to get Home Assistant external URL. Have you set external URLs in Configuration -> General?'
                )

            endpoint_url = stream.endpoint_url(StreamType.HLS)
            stream_url = f'{external_url}{endpoint_url}'

        return {
            'stream_url': stream_url,
            'protocol': 'hls'
        }

    async def _async_request_stream(self, entity_id: str) -> Stream:
        camera_entity = _get_camera_from_entity_id(self.hass, self.state.entity_id)
        stream = await camera_entity.async_create_stream()

        if not stream:
            raise SmartHomeError(
                ERR_NOT_SUPPORTED_IN_CURRENT_MODE,
                f'{entity_id} does not support play stream service'
            )

        stream.add_provider(StreamType.HLS)
        await stream.start()
        stream.endpoint_url(StreamType.HLS)

        return stream
