"""Implement the Yandex Smart Home video_stream capabilities."""
import logging

from homeassistant.components import camera
from homeassistant.components.camera import StreamType, _get_camera_from_entity_id
from homeassistant.components.stream import Stream
from homeassistant.core import Context
from homeassistant.helpers import network
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .capability import ActionOnlyCapability, register_capability
from .cloud_stream import CloudStream
from .const import CLOUD_STREAMS, DOMAIN, ERR_NOT_SUPPORTED_IN_CURRENT_MODE
from .error import SmartHomeError
from .schema import (
    CapabilityType,
    GetStreamInstanceActionResultValue,
    GetStreamInstanceActionState,
    VideoStreamCapabilityInstance,
    VideoStreamCapabilityParameters,
)

_LOGGER = logging.getLogger(__name__)


@register_capability
class VideoStreamCapability(ActionOnlyCapability):
    """Capability to stream from cameras."""

    type = CapabilityType.VIDEO_STREAM
    instance = VideoStreamCapabilityInstance.GET_STREAM

    @property
    def supported(self) -> bool:
        """Test if the capability is supported for its state."""
        return self.state.domain == camera.DOMAIN and bool(self._state_features & camera.CameraEntityFeature.STREAM)

    @property
    def parameters(self) -> VideoStreamCapabilityParameters:
        """Return parameters for a devices request."""
        return VideoStreamCapabilityParameters(protocols=["hls"])

    async def set_instance_state(
        self, context: Context, state: GetStreamInstanceActionState
    ) -> GetStreamInstanceActionResultValue:
        """Change capability instance state."""
        entity_id = self.state.entity_id
        stream = await self._async_request_stream(entity_id)

        if self._config.use_cloud_stream:
            cloud_stream = self._hass.data[DOMAIN][CLOUD_STREAMS].get(entity_id)
            if not cloud_stream:
                cloud_stream = CloudStream(self._hass, stream, async_get_clientsession(self._hass))
                self._hass.data[DOMAIN][CLOUD_STREAMS][entity_id] = cloud_stream

            await cloud_stream.start()
            stream_url = cloud_stream.stream_url
            if not stream_url:
                raise SmartHomeError(ERR_NOT_SUPPORTED_IN_CURRENT_MODE, "Failed to start stream")
        else:
            try:
                external_url = network.get_url(self._hass, allow_internal=False)
            except network.NoURLAvailableError:
                raise SmartHomeError(
                    ERR_NOT_SUPPORTED_IN_CURRENT_MODE,
                    "Unable to get Home Assistant external URL. "
                    "Have you set external URLs in Configuration -> General?",
                )

            endpoint_url = stream.endpoint_url(StreamType.HLS)
            stream_url = f"{external_url}{endpoint_url}"

        return GetStreamInstanceActionResultValue(stream_url=stream_url, protocol="hls")

    async def _async_request_stream(self, entity_id: str) -> Stream:
        camera_entity = _get_camera_from_entity_id(self._hass, self.state.entity_id)
        stream = await camera_entity.async_create_stream()

        if not stream:
            raise SmartHomeError(ERR_NOT_SUPPORTED_IN_CURRENT_MODE, f"{entity_id} does not support play stream service")

        stream.add_provider(StreamType.HLS)

        await stream.start()

        stream.endpoint_url(StreamType.HLS)

        return stream
