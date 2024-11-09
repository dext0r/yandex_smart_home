"""Implement the Yandex Smart Home video_stream capabilities."""

# pyright: reportAttributeAccessIssue=information

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components import camera
from homeassistant.components.camera import StreamType
from homeassistant.components.stream import Stream
from homeassistant.core import Context
from homeassistant.helpers import network
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .capability import STATE_CAPABILITIES_REGISTRY, ActionOnlyCapabilityMixin, StateCapability
from .cloud_stream import CloudStreamManager
from .const import DOMAIN
from .helpers import APIError
from .schema import (
    CapabilityType,
    GetStreamInstanceActionResultValue,
    GetStreamInstanceActionState,
    ResponseCode,
    VideoStreamCapabilityInstance,
    VideoStreamCapabilityParameters,
)

try:
    from homeassistant.components.camera import get_camera_from_entity_id
except ImportError:  # pragma: no cover
    from homeassistant.components.camera import (  # type: ignore[no-redef]
        _get_camera_from_entity_id as get_camera_from_entity_id,
    )


if TYPE_CHECKING:
    from . import YandexSmartHome


class VideoStreamCapability(ActionOnlyCapabilityMixin, StateCapability[GetStreamInstanceActionState]):
    """Capability to stream from cameras."""

    type = CapabilityType.VIDEO_STREAM
    instance = VideoStreamCapabilityInstance.GET_STREAM

    @property
    def supported(self) -> bool:
        """Test if the capability is supported."""
        return self.state.domain == camera.DOMAIN and bool(self._state_features & camera.CameraEntityFeature.STREAM)

    @property
    def parameters(self) -> VideoStreamCapabilityParameters:
        """Return parameters for a devices request."""
        return VideoStreamCapabilityParameters(protocols=["hls"])

    async def set_instance_state(
        self, context: Context, state: GetStreamInstanceActionState
    ) -> GetStreamInstanceActionResultValue:
        """Change capability instance state."""
        component: YandexSmartHome = self._hass.data[DOMAIN]
        entity_id = self.state.entity_id
        stream = await self._async_request_stream(entity_id)

        if self._entry_data.use_cloud_stream:
            cloud_stream = component.cloud_streams.get(entity_id)
            if not cloud_stream:
                cloud_stream = CloudStreamManager(self._hass, stream, async_get_clientsession(self._hass))
                component.cloud_streams[entity_id] = cloud_stream

            await cloud_stream.async_start()
            stream_url = cloud_stream.stream_url
            if not stream_url:
                raise APIError(ResponseCode.NOT_SUPPORTED_IN_CURRENT_MODE, "Failed to start stream")
        else:
            try:
                external_url = network.get_url(self._hass, allow_internal=False)
            except network.NoURLAvailableError:
                raise APIError(
                    ResponseCode.NOT_SUPPORTED_IN_CURRENT_MODE,
                    "Missing Home Assistant external URL. Have you set external URLs in Configuration -> General?",
                )

            endpoint_url = stream.endpoint_url(StreamType.HLS)
            stream_url = f"{external_url}{endpoint_url}"

        return GetStreamInstanceActionResultValue(stream_url=stream_url, protocol="hls")

    async def _async_request_stream(self, entity_id: str) -> Stream:
        camera_entity = get_camera_from_entity_id(self._hass, self.state.entity_id)
        stream = await camera_entity.async_create_stream()

        if not stream:
            raise APIError(
                ResponseCode.NOT_SUPPORTED_IN_CURRENT_MODE, f"{entity_id} does not support play stream service"
            )

        stream.add_provider(StreamType.HLS)

        await stream.start()

        stream.endpoint_url(StreamType.HLS)

        return stream


STATE_CAPABILITIES_REGISTRY.register(VideoStreamCapability)
