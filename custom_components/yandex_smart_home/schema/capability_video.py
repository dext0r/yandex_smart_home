"""Schema for video_stream capability.

https://yandex.ru/dev/dialogs/smart-home/doc/concepts/video_stream.html
"""
from enum import StrEnum
from typing import Literal

from .base import APIModel

StreamProtocols = list[Literal["hls"]]


class VideoStreamCapabilityInstance(StrEnum):
    """Instance of a video_stream capability."""

    GET_STREAM = "get_stream"


class VideoStreamCapabilityParameters(APIModel):
    """Parameters of a video_stream capability."""

    protocols: StreamProtocols


class GetStreamInstanceActionStateValue(APIModel):
    """New state value for a get_stream instance."""

    protocols: StreamProtocols


class GetStreamInstanceActionState(APIModel):
    """New value for a get_stream instance."""

    instance: Literal[VideoStreamCapabilityInstance.GET_STREAM]
    value: GetStreamInstanceActionStateValue


class GetStreamInstanceActionResultValue(APIModel):
    """New value after a get_stream instance state changed."""

    stream_url: str
    protocol: Literal["hls"]
