"""Schema for video_stream capability.

https://yandex.ru/dev/dialogs/smart-home/doc/concepts/video_stream.html
"""
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel

StreamProtocols = list[Literal["hls"]]


class VideoStreamCapabilityInstance(StrEnum):
    GET_STREAM = "get_stream"


class VideoStreamCapabilityParameters(BaseModel):
    protocols: StreamProtocols


class GetStreamInstanceActionStateValue(BaseModel):
    protocols: StreamProtocols


class GetStreamInstanceActionState(BaseModel):
    instance: Literal[VideoStreamCapabilityInstance.GET_STREAM]
    value: GetStreamInstanceActionStateValue


class GetStreamInstanceActionResultValue(BaseModel):
    stream_url: str
    protocol: Literal["hls"]
