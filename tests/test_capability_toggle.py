from typing import cast

from homeassistant.components import cover, fan, media_player, vacuum
from homeassistant.const import ATTR_ENTITY_ID, ATTR_SUPPORTED_FEATURES, STATE_ON
from homeassistant.core import Context, State
from pytest_homeassistant_custom_component.common import async_mock_service

from custom_components.yandex_smart_home.capability_toggle import ToggleCapability
from custom_components.yandex_smart_home.schema import (
    CapabilityType,
    ToggleCapabilityInstance,
    ToggleCapabilityInstanceActionState,
)

from . import BASIC_CONFIG, MockConfig
from .test_capability import assert_exact_one_capability, assert_no_capabilities, get_exact_one_capability


def _action_state_on(instance: ToggleCapabilityInstance) -> ToggleCapabilityInstanceActionState:
    return ToggleCapabilityInstanceActionState(instance=instance, value=True)


def _action_state_off(instance: ToggleCapabilityInstance) -> ToggleCapabilityInstanceActionState:
    return ToggleCapabilityInstanceActionState(instance=instance, value=False)


async def test_capability_mute(hass):
    state = State("media_player.test", STATE_ON)
    assert_no_capabilities(hass, BASIC_CONFIG, state, CapabilityType.TOGGLE, ToggleCapabilityInstance.MUTE)

    state = State("media_player.test", STATE_ON)
    config = MockConfig(entity_config={state.entity_id: {"features": ["volume_mute"]}})
    assert_exact_one_capability(hass, config, state, CapabilityType.TOGGLE, ToggleCapabilityInstance.MUTE)

    state = State(
        "media_player.test", STATE_ON, {ATTR_SUPPORTED_FEATURES: media_player.MediaPlayerEntityFeature.VOLUME_MUTE}
    )
    cap = cast(
        ToggleCapability,
        get_exact_one_capability(hass, BASIC_CONFIG, state, CapabilityType.TOGGLE, ToggleCapabilityInstance.MUTE),
    )

    assert cap.retrievable is False
    assert cap.parameters.dict() == {"instance": "mute"}
    assert cap.get_value() is False

    calls = async_mock_service(hass, media_player.DOMAIN, media_player.SERVICE_VOLUME_MUTE)
    await cap.set_instance_state(Context(), _action_state_on(ToggleCapabilityInstance.MUTE))
    await cap.set_instance_state(Context(), _action_state_off(ToggleCapabilityInstance.MUTE))
    assert len(calls) == 2
    assert calls[0].data[ATTR_ENTITY_ID] == state.entity_id
    assert calls[0].data[media_player.ATTR_MEDIA_VOLUME_MUTED] is True
    assert calls[1].data[ATTR_ENTITY_ID] == state.entity_id
    assert calls[1].data[media_player.ATTR_MEDIA_VOLUME_MUTED] is False

    state = State(
        "media_player.test",
        STATE_ON,
        {
            ATTR_SUPPORTED_FEATURES: media_player.MediaPlayerEntityFeature.VOLUME_MUTE,
            media_player.ATTR_MEDIA_VOLUME_MUTED: True,
        },
    )
    cap = cast(
        ToggleCapability,
        get_exact_one_capability(hass, BASIC_CONFIG, state, CapabilityType.TOGGLE, ToggleCapabilityInstance.MUTE),
    )
    assert cap.retrievable is True
    assert cap.get_value() is True

    calls = async_mock_service(hass, media_player.DOMAIN, media_player.SERVICE_VOLUME_MUTE)
    await cap.set_instance_state(Context(), _action_state_on(ToggleCapabilityInstance.MUTE))
    await cap.set_instance_state(Context(), _action_state_off(ToggleCapabilityInstance.MUTE))
    assert len(calls) == 2
    assert calls[0].data[ATTR_ENTITY_ID] == state.entity_id
    assert calls[0].data[media_player.ATTR_MEDIA_VOLUME_MUTED] is True
    assert calls[1].data[ATTR_ENTITY_ID] == state.entity_id
    assert calls[1].data[media_player.ATTR_MEDIA_VOLUME_MUTED] is False


async def test_capability_pause_media_player(hass):
    state = State("media_player.test", STATE_ON)
    assert_no_capabilities(hass, BASIC_CONFIG, state, CapabilityType.TOGGLE, ToggleCapabilityInstance.PAUSE)

    state = State("media_player.test", STATE_ON)
    config = MockConfig(entity_config={state.entity_id: {"features": ["play_pause"]}})
    assert_exact_one_capability(hass, config, state, CapabilityType.TOGGLE, ToggleCapabilityInstance.PAUSE)

    for s in [media_player.STATE_IDLE, media_player.STATE_OFF]:
        state = State(
            "media_player.test",
            s,
            {
                ATTR_SUPPORTED_FEATURES: media_player.MediaPlayerEntityFeature.PAUSE
                | media_player.MediaPlayerEntityFeature.PLAY
            },
        )
        cap = cast(
            ToggleCapability,
            get_exact_one_capability(hass, BASIC_CONFIG, state, CapabilityType.TOGGLE, ToggleCapabilityInstance.PAUSE),
        )
        assert cap.retrievable is True
        assert cap.parameters.dict() == {"instance": "pause"}
        assert cap.get_value() is True

    state = State(
        "media_player.test",
        media_player.STATE_PLAYING,
        {
            ATTR_SUPPORTED_FEATURES: media_player.MediaPlayerEntityFeature.PAUSE
            | media_player.MediaPlayerEntityFeature.PLAY
        },
    )
    cap = cast(
        ToggleCapability,
        get_exact_one_capability(hass, BASIC_CONFIG, state, CapabilityType.TOGGLE, ToggleCapabilityInstance.PAUSE),
    )
    assert cap.get_value() is False

    on_calls = async_mock_service(hass, media_player.DOMAIN, media_player.SERVICE_MEDIA_PAUSE)
    await cap.set_instance_state(Context(), _action_state_on(ToggleCapabilityInstance.PAUSE))
    assert len(on_calls) == 1
    assert on_calls[0].data == {ATTR_ENTITY_ID: state.entity_id}

    off_calls = async_mock_service(hass, media_player.DOMAIN, media_player.SERVICE_MEDIA_PLAY)
    await cap.set_instance_state(Context(), _action_state_off(ToggleCapabilityInstance.PAUSE))
    assert len(off_calls) == 1
    assert off_calls[0].data == {ATTR_ENTITY_ID: state.entity_id}


async def test_capability_pause_cover(hass):
    state = State("cover.test", STATE_ON)
    assert_no_capabilities(hass, BASIC_CONFIG, state, CapabilityType.TOGGLE, ToggleCapabilityInstance.PAUSE)

    for s in [cover.STATE_OPEN, cover.STATE_CLOSED, cover.STATE_CLOSING, cover.STATE_CLOSING]:
        state = State("cover.test", s, {ATTR_SUPPORTED_FEATURES: cover.CoverEntityFeature.STOP})
        cap = cast(
            ToggleCapability,
            get_exact_one_capability(hass, BASIC_CONFIG, state, CapabilityType.TOGGLE, ToggleCapabilityInstance.PAUSE),
        )
        assert cap.retrievable is False
        assert cap.reportable is False
        assert cap.parameters.dict() == {"instance": "pause"}
        assert cap.get_value() is None

    calls = async_mock_service(hass, cover.DOMAIN, cover.SERVICE_STOP_COVER)
    await cap.set_instance_state(Context(), _action_state_on(ToggleCapabilityInstance.PAUSE))
    await cap.set_instance_state(Context(), _action_state_off(ToggleCapabilityInstance.PAUSE))
    assert len(calls) == 2
    assert calls[0].data == {ATTR_ENTITY_ID: state.entity_id}
    assert calls[1].data == {ATTR_ENTITY_ID: state.entity_id}


async def test_capability_pause_vacuum(hass):
    state = State("vacuum.test", STATE_ON)
    assert_no_capabilities(hass, BASIC_CONFIG, state, CapabilityType.TOGGLE, ToggleCapabilityInstance.PAUSE)

    for s in vacuum.STATES:
        state = State("vacuum.test", s, {ATTR_SUPPORTED_FEATURES: vacuum.VacuumEntityFeature.PAUSE})
        cap = cast(
            ToggleCapability,
            get_exact_one_capability(hass, BASIC_CONFIG, state, CapabilityType.TOGGLE, ToggleCapabilityInstance.PAUSE),
        )
        assert cap.retrievable is True
        assert cap.parameters.dict() == {"instance": "pause"}
        assert cap.get_value() is False

    state = State("vacuum.test", vacuum.STATE_PAUSED, {ATTR_SUPPORTED_FEATURES: vacuum.VacuumEntityFeature.PAUSE})
    cap = cast(
        ToggleCapability,
        get_exact_one_capability(hass, BASIC_CONFIG, state, CapabilityType.TOGGLE, ToggleCapabilityInstance.PAUSE),
    )
    assert cap.get_value() is True

    on_calls = async_mock_service(hass, vacuum.DOMAIN, vacuum.SERVICE_PAUSE)
    await cap.set_instance_state(Context(), _action_state_on(ToggleCapabilityInstance.PAUSE))
    assert len(on_calls) == 1
    assert on_calls[0].data == {ATTR_ENTITY_ID: state.entity_id}

    off_calls = async_mock_service(hass, vacuum.DOMAIN, vacuum.SERVICE_START)
    await cap.set_instance_state(Context(), _action_state_off(ToggleCapabilityInstance.PAUSE))
    assert len(off_calls) == 1
    assert off_calls[0].data == {ATTR_ENTITY_ID: state.entity_id}


async def test_capability_oscillation(hass):
    state = State("fan.test", STATE_ON)
    assert_no_capabilities(hass, BASIC_CONFIG, state, CapabilityType.TOGGLE, ToggleCapabilityInstance.OSCILLATION)

    state = State("fan.test", STATE_ON, {ATTR_SUPPORTED_FEATURES: fan.FanEntityFeature.OSCILLATE})
    cap = cast(
        ToggleCapability,
        get_exact_one_capability(
            hass, BASIC_CONFIG, state, CapabilityType.TOGGLE, ToggleCapabilityInstance.OSCILLATION
        ),
    )
    assert cap.retrievable is True
    assert cap.parameters.dict() == {"instance": "oscillation"}
    assert cap.get_value() is False

    state = State(
        "fan.test", STATE_ON, {ATTR_SUPPORTED_FEATURES: fan.FanEntityFeature.OSCILLATE, fan.ATTR_OSCILLATING: True}
    )
    cap = cast(
        ToggleCapability,
        get_exact_one_capability(
            hass, BASIC_CONFIG, state, CapabilityType.TOGGLE, ToggleCapabilityInstance.OSCILLATION
        ),
    )
    assert cap.get_value() is True

    state = State(
        "fan.test", STATE_ON, {ATTR_SUPPORTED_FEATURES: fan.FanEntityFeature.OSCILLATE, fan.ATTR_OSCILLATING: False}
    )
    cap = cast(
        ToggleCapability,
        get_exact_one_capability(
            hass, BASIC_CONFIG, state, CapabilityType.TOGGLE, ToggleCapabilityInstance.OSCILLATION
        ),
    )
    assert cap.get_value() is False

    calls = async_mock_service(hass, fan.DOMAIN, fan.SERVICE_OSCILLATE)
    await cap.set_instance_state(Context(), _action_state_on(ToggleCapabilityInstance.OSCILLATION))
    await cap.set_instance_state(Context(), _action_state_off(ToggleCapabilityInstance.OSCILLATION))
    assert len(calls) == 2
    assert calls[0].data[ATTR_ENTITY_ID] == state.entity_id
    assert calls[0].data[fan.ATTR_OSCILLATING] is True
    assert calls[1].data[ATTR_ENTITY_ID] == state.entity_id
    assert calls[1].data[fan.ATTR_OSCILLATING] is False
