from pytest_homeassistant_custom_component.common import load_fixture

from custom_components.yandex_smart_home.schema import ActionRequest, GetStreamInstanceActionStateValue
from custom_components.yandex_smart_home.schema.capability import *
from custom_components.yandex_smart_home.schema.capability_color import *
from custom_components.yandex_smart_home.schema.capability_mode import *


def test_devices_action_request() -> None:
    request = ActionRequest.parse_raw(load_fixture("devices_action.json"))
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
