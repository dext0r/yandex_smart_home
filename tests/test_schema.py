import pytest
from pytest_homeassistant_custom_component.common import load_fixture

from custom_components.yandex_smart_home.schema import (
    ActionRequest,
    EventPropertyInstance,
    EventPropertyParameters,
    GasInstanceEvent,
    GetStreamInstanceActionStateValue,
)
from custom_components.yandex_smart_home.schema.capability import *
from custom_components.yandex_smart_home.schema.capability_color import *
from custom_components.yandex_smart_home.schema.capability_mode import *


def test_devices_action_request() -> None:
    request = ActionRequest.model_validate_json(load_fixture("devices_action.json"))
    assert len(request.payload.devices) == 1
    assert len(request.payload.devices[0].capabilities) == 10

    assert request.payload.devices[0].capabilities[0] == OnOffCapabilityInstanceAction(
        state=OnOffCapabilityInstanceActionState(instance=OnOffCapabilityInstance.ON, value=False),
    )
    assert request.payload.devices[0].capabilities[1] == VideoStreamCapabilityInstanceAction(
        state=GetStreamInstanceActionState(
            instance=VideoStreamCapabilityInstance.GET_STREAM,
            value=GetStreamInstanceActionStateValue(protocols=["hls"]),
        ),
    )
    assert request.payload.devices[0].capabilities[2] == ColorSettingCapabilityInstanceAction(
        state=RGBInstanceActionState(value=14210514),
    )
    assert request.payload.devices[0].capabilities[3] == ColorSettingCapabilityInstanceAction(
        state=TemperatureKInstanceActionState(value=5100),
    )
    assert request.payload.devices[0].capabilities[4] == ColorSettingCapabilityInstanceAction(
        state=SceneInstanceActionState(value=ColorScene.PARTY),
    )
    assert request.payload.devices[0].capabilities[5] == ModeCapabilityInstanceAction(
        state=ModeCapabilityInstanceActionState(
            instance=ModeCapabilityInstance.THERMOSTAT, value=ModeCapabilityMode.HEAT
        ),
    )
    assert request.payload.devices[0].capabilities[6] == RangeCapabilityInstanceAction(
        state=RangeCapabilityInstanceActionState(
            instance=RangeCapabilityInstance.BRIGHTNESS, value=50.0, relative=False
        ),
    )
    assert request.payload.devices[0].capabilities[7] == RangeCapabilityInstanceAction(
        state=RangeCapabilityInstanceActionState(instance=RangeCapabilityInstance.VOLUME, value=10.0, relative=True),
    )
    assert request.payload.devices[0].capabilities[8] == RangeCapabilityInstanceAction(
        state=RangeCapabilityInstanceActionState(instance=RangeCapabilityInstance.OPEN, value=-5.5, relative=False),
    )
    assert request.payload.devices[0].capabilities[9] == ToggleCapabilityInstanceAction(
        state=ToggleCapabilityInstanceActionState(instance=ToggleCapabilityInstance.IONIZATION, value=False),
    )


def test_devices_action_request_vk() -> None:
    request = ActionRequest.model_validate_json(load_fixture("devices_action_vk.json"))
    assert len(request.payload.devices) == 1
    assert len(request.payload.devices[0].capabilities) == 1

    assert request.payload.devices[0].capabilities[0] == RangeCapabilityInstanceAction(
        state=RangeCapabilityInstanceActionState(instance=RangeCapabilityInstance.VOLUME, value=54.0, relative=False),
    )


def test_range_capability_parameters() -> None:
    with pytest.raises(ValueError):
        RangeCapabilityParameters(instance=RangeCapabilityInstance.BRIGHTNESS, random_access=False)

    RangeCapabilityParameters(instance=RangeCapabilityInstance.CHANNEL, random_access=False)


def test_color_capability_parameters() -> None:
    with pytest.raises(ValueError):
        ColorSettingCapabilityParameters()

    ColorSettingCapabilityParameters(color_model=CapabilityParameterColorModel.RGB)
    ColorSettingCapabilityParameters(temperature_k=CapabilityParameterTemperatureK(min=0, max=0))
    ColorSettingCapabilityParameters(color_scene=CapabilityParameterColorScene(scenes=[{"id": ColorScene.ALARM}]))


def test_event_property_parameters() -> None:
    p = EventPropertyParameters[GasInstanceEvent](instance=EventPropertyInstance.GAS)
    assert p.events == [{"value": "detected"}, {"value": "not_detected"}, {"value": "high"}]

    p = EventPropertyParameters[GasInstanceEvent](
        instance=EventPropertyInstance.GAS, events=[{"value": GasInstanceEvent.DETECTED}]
    )
    assert p.events == [{"value": "detected"}]
