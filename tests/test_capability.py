from homeassistant.core import HomeAssistant, State
from homeassistant.const import ATTR_SUPPORTED_FEATURES

from custom_components.yandex_smart_home.helpers import Config
# noinspection PyProtectedMember
from custom_components.yandex_smart_home.capability import CAPABILITIES, _Capability


def get_exact_one_capability(hass: HomeAssistant, config: Config, state: State, capability_type: str) -> _Capability:
    caps = []

    for Capability in CAPABILITIES:
        capability = Capability(hass, config, state)

        if capability.type != capability_type:
            continue

        if capability.supported(state.domain,
                                state.attributes.get(ATTR_SUPPORTED_FEATURES, 0),
                                config.get_entity_config(state.entity_id),
                                state.attributes):
            caps.append(capability)

    assert len(caps) == 1
    return caps[0]
