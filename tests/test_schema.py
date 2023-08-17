from pytest_homeassistant_custom_component.common import load_fixture

from custom_components.yandex_smart_home.schema import DevicesActionRequest, GetStreamInstanceActionStateValue
from custom_components.yandex_smart_home.schema.capability import *
from custom_components.yandex_smart_home.schema.capability_color import *


def test_devices_action_request():
    request = DevicesActionRequest.parse_raw(load_fixture("devices_action.json"))
    assert len(request.payload.devices) == 1
    assert len(request.payload.devices[0].capabilities) == 10

    assert request.payload.devices[0].capabilities[0] == OnOffCapabilityInstanceAction(
        type=CapabilityType.ON_OFF,
        state=OnOffCapabilityInstanceActionState(instance=OnOffCapabilityInstance.ON, value=False),
    )
    assert request.payload.devices[0].capabilities[1] == VideoStreamCapabilityInstanceAction(
        type=CapabilityType.VIDEO_STREAM,
        state=GetStreamInstanceActionState(
            instance=VideoStreamCapabilityInstance.GET_STREAM,
            value=GetStreamInstanceActionStateValue(protocols=["hls"]),
        ),
    )
    assert request.payload.devices[0].capabilities[2] == ColorSettingCapabilityInstanceAction(
        type=CapabilityType.COLOR_SETTING,
        state=RGBInstanceActionState(instance=ColorSettingCapabilityInstance.RGB, value=14210514),
    )
    assert request.payload.devices[0].capabilities[3] == ColorSettingCapabilityInstanceAction(
        type=CapabilityType.COLOR_SETTING,
        state=TemperatureKInstanceActionState(instance=ColorSettingCapabilityInstance.TEMPERATURE_K, value=5100),
    )
    assert request.payload.devices[0].capabilities[4] == ColorSettingCapabilityInstanceAction(
        type=CapabilityType.COLOR_SETTING,
        state=SceneInstanceActionState(instance=ColorSettingCapabilityInstance.SCENE, value=ColorScene.PARTY),
    )
    assert request.payload.devices[0].capabilities[5] == ModeCapabilityInstanceAction(
        type=CapabilityType.MODE,
        state=ModeCapabilityInstanceActionState(
            instance=ModeCapabilityInstance.THERMOSTAT, value=ModeCapabilityMode.HEAT
        ),
    )
    assert request.payload.devices[0].capabilities[6] == RangeCapabilityInstanceAction(
        type=CapabilityType.RANGE,
        state=RangeCapabilityInstanceActionState(
            instance=RangeCapabilityInstance.BRIGHTNESS, value=50.0, relative=False
        ),
    )
    assert request.payload.devices[0].capabilities[7] == RangeCapabilityInstanceAction(
        type=CapabilityType.RANGE,
        state=RangeCapabilityInstanceActionState(instance=RangeCapabilityInstance.VOLUME, value=10.0, relative=True),
    )
    assert request.payload.devices[0].capabilities[8] == RangeCapabilityInstanceAction(
        type=CapabilityType.RANGE,
        state=RangeCapabilityInstanceActionState(instance=RangeCapabilityInstance.OPEN, value=-5.5, relative=False),
    )
    assert request.payload.devices[0].capabilities[9] == ToggleCapabilityInstanceAction(
        type=CapabilityType.TOGGLE,
        state=ToggleCapabilityInstanceActionState(instance=ToggleCapabilityInstance.IONIZATION, value=False),
    )
