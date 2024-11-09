# pyright: reportOptionalMemberAccess=false
from typing import cast
from unittest.mock import patch

from homeassistant.components.camera import Camera, CameraEntityFeature, DynamicStreamSettings
from homeassistant.components.stream import OUTPUT_IDLE_TIMEOUT, Stream, StreamOutput, StreamSettings
from homeassistant.const import ATTR_SUPPORTED_FEATURES, STATE_IDLE
from homeassistant.core import Context, HomeAssistant, State
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.yandex_smart_home import DOMAIN, YandexSmartHome
from custom_components.yandex_smart_home.capability_video import VideoStreamCapability
from custom_components.yandex_smart_home.config_flow import ConfigFlowHandler
from custom_components.yandex_smart_home.const import (
    CONF_CLOUD_STREAM,
    CONF_CONNECTION_TYPE,
    CONF_SETTINGS,
    ConnectionType,
)
from custom_components.yandex_smart_home.helpers import APIError
from custom_components.yandex_smart_home.schema import (
    CapabilityType,
    GetStreamInstanceActionState,
    GetStreamInstanceActionStateValue,
    ResponseCode,
    VideoStreamCapabilityInstance,
)

from . import BASIC_ENTRY_DATA, MockConfigEntryData
from .test_capability import assert_no_capabilities, get_exact_one_capability

try:
    from homeassistant.core_config import async_process_ha_core_config
except ImportError:
    from homeassistant.config import async_process_ha_core_config  # pyright: ignore[reportAttributeAccessIssue]


ACTION_STATE = GetStreamInstanceActionState(
    instance=VideoStreamCapabilityInstance.GET_STREAM,
    value=GetStreamInstanceActionStateValue(protocols=["hls"]),
)


class MockStream(Stream):
    def __init__(self, hass: HomeAssistant):
        super().__init__(
            hass,
            "test",
            {},
            StreamSettings(
                ll_hls=True,
                min_segment_duration=0,
                part_target_duration=0,
                hls_advance_part_limit=0,
                hls_part_timeout=0,
            ),
            DynamicStreamSettings(),
        )

    def endpoint_url(self, fmt: str) -> str:
        return "/foo"

    def add_provider(self, fmt: str, timeout: int = OUTPUT_IDLE_TIMEOUT) -> StreamOutput: ...

    async def start(self) -> None:
        pass


class MockCamera(Camera):
    def camera_image(self, width: int | None = None, height: int | None = None) -> bytes | None:
        pass

    def turn_off(self) -> None:
        pass

    def turn_on(self) -> None:
        pass

    def enable_motion_detection(self) -> None:
        pass

    def disable_motion_detection(self) -> None:
        pass

    async def async_create_stream(self) -> Stream | None:
        return MockStream(self.hass)


class MockCameraUnsupported(MockCamera):
    async def async_create_stream(self) -> Stream | None:
        return None


async def test_capability_video_stream_supported(hass):
    state = State("camera.test", STATE_IDLE, {ATTR_SUPPORTED_FEATURES: CameraEntityFeature.STREAM})
    cap = cast(
        VideoStreamCapability,
        get_exact_one_capability(
            hass, BASIC_ENTRY_DATA, state, CapabilityType.VIDEO_STREAM, VideoStreamCapabilityInstance.GET_STREAM
        ),
    )
    assert cap.parameters.dict() == {"protocols": ["hls"]}
    assert cap.get_value() is None
    assert cap.retrievable is False
    assert cap.reportable is False

    state = State("camera.no_stream", STATE_IDLE)
    assert_no_capabilities(
        hass, BASIC_ENTRY_DATA, state, CapabilityType.VIDEO_STREAM, VideoStreamCapabilityInstance.GET_STREAM
    )


async def test_capability_video_stream_request_stream(hass):
    state = State("camera.test", STATE_IDLE, {ATTR_SUPPORTED_FEATURES: CameraEntityFeature.STREAM})
    cap = VideoStreamCapability(hass, BASIC_ENTRY_DATA, state)

    with patch(
        "custom_components.yandex_smart_home.capability_video.get_camera_from_entity_id",
        return_value=MockCamera(),
    ):
        assert isinstance(await cap._async_request_stream(state.entity_id), MockStream)

    with patch(
        "custom_components.yandex_smart_home.capability_video.get_camera_from_entity_id",
        return_value=MockCameraUnsupported(),
    ):
        with pytest.raises(APIError) as e:
            await cap._async_request_stream(state.entity_id)
        assert e.value.code == ResponseCode.NOT_SUPPORTED_IN_CURRENT_MODE
        assert e.value.message == "camera.test does not support play stream service"


async def test_capability_video_stream_direct(hass_platform_direct, config_entry_direct):
    hass = hass_platform_direct
    entry_data = MockConfigEntryData(entry=config_entry_direct)
    state = State("camera.test", STATE_IDLE, {ATTR_SUPPORTED_FEATURES: CameraEntityFeature.STREAM})

    cap = cast(
        VideoStreamCapability,
        get_exact_one_capability(
            hass, entry_data, state, CapabilityType.VIDEO_STREAM, VideoStreamCapabilityInstance.GET_STREAM
        ),
    )
    stream = MockStream(hass)

    with patch.object(cap, "_async_request_stream", return_value=stream):
        with pytest.raises(APIError) as e:
            await cap.set_instance_state(Context(), ACTION_STATE)
        assert e.value.code == ResponseCode.NOT_SUPPORTED_IN_CURRENT_MODE
        assert (
            e.value.message
            == "Missing Home Assistant external URL. Have you set external URLs in Configuration -> General?"
        )

    await async_process_ha_core_config(hass, {"external_url": "https://example.com"})

    with patch.object(cap, "_async_request_stream", return_value=stream):
        assert (await cap.set_instance_state(Context(), ACTION_STATE)).dict() == {
            "protocol": "hls",
            "stream_url": "https://example.com/foo",
        }


@pytest.mark.parametrize("connection_type", [ConnectionType.DIRECT, ConnectionType.CLOUD])
async def test_capability_video_stream_cloud(hass_platform_direct, connection_type):
    hass = hass_platform_direct
    component: YandexSmartHome = hass.data[DOMAIN]
    entry = MockConfigEntry(
        domain=DOMAIN, version=ConfigFlowHandler.VERSION, data={CONF_CONNECTION_TYPE: connection_type}
    )
    entry_data = MockConfigEntryData(entry=entry, yaml_config={CONF_SETTINGS: {CONF_CLOUD_STREAM: True}})
    state = State("camera.test", STATE_IDLE, {ATTR_SUPPORTED_FEATURES: CameraEntityFeature.STREAM})

    cap = cast(
        VideoStreamCapability,
        get_exact_one_capability(
            hass, entry_data, state, CapabilityType.VIDEO_STREAM, VideoStreamCapabilityInstance.GET_STREAM
        ),
    )
    stream = MockStream(hass)

    with patch.object(cap, "_async_request_stream", return_value=stream), patch(
        "custom_components.yandex_smart_home.cloud_stream.CloudStreamManager.async_start"
    ) as mock_start_cloud_stream:
        with pytest.raises(APIError) as e:
            await cap.set_instance_state(Context(), ACTION_STATE)
        assert e.value.code == ResponseCode.NOT_SUPPORTED_IN_CURRENT_MODE
        assert e.value.message == "Failed to start stream"
        mock_start_cloud_stream.assert_called_once()

        assert len(component.cloud_streams) == 1
        cloud_stream = component.cloud_streams[state.entity_id]
        cloud_stream._running_stream_id = "foo"
        assert (await cap.set_instance_state(Context(), ACTION_STATE)).dict() == {
            "protocol": "hls",
            "stream_url": "https://stream.yaha-cloud.ru/foo/master_playlist.m3u8",
        }

        assert component.cloud_streams[state.entity_id] == cloud_stream
