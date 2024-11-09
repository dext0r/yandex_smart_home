"""Global fixtures for yandex_smart_home integration."""

import asyncio
import logging
from typing import Any, Generator
from unittest.mock import patch

from homeassistant.auth.models import User
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.demo.binary_sensor import DemoBinarySensor
from homeassistant.components.demo.light import DemoLight
from homeassistant.components.demo.sensor import DemoSensor
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import CONF_ID, CONF_PLATFORM, CONF_TOKEN, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entityfilter
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.syrupy import HomeAssistantSnapshotExtension
from pytest_homeassistant_custom_component.typing import ClientSessionGenerator
from syrupy import SnapshotAssertion

from custom_components.yandex_smart_home import DOMAIN
from custom_components.yandex_smart_home.config_flow import ConfigFlowHandler
from custom_components.yandex_smart_home.const import (
    CONF_CLOUD_INSTANCE,
    CONF_CLOUD_INSTANCE_CONNECTION_TOKEN,
    CONF_CLOUD_INSTANCE_ID,
    CONF_CONNECTION_TYPE,
    CONF_FILTER,
    CONF_FILTER_SOURCE,
    CONF_SKILL,
    CONF_USER_ID,
    ConnectionType,
    EntityFilterSource,
)
from custom_components.yandex_smart_home.helpers import SmartHomePlatform

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def enable_custom_integrations(enable_custom_integrations: None) -> None:
    return enable_custom_integrations


@pytest.fixture(autouse=True)
def debug_logging() -> None:
    logging.getLogger("custom_components.yandex_smart_home").setLevel(logging.DEBUG)


@pytest.fixture(name="skip_notifications", autouse=True)
def skip_notifications_fixture() -> Generator[Any, Any, Any]:
    """Skip notification calls."""
    with patch("homeassistant.components.persistent_notification.async_create"), patch(
        "homeassistant.components.persistent_notification.async_dismiss"
    ):
        yield


@pytest.fixture
def socket_enabled(socket_enabled: None) -> None:
    """Mark socket_enabled as fixture."""
    return socket_enabled


@pytest.fixture
def aiohttp_client(aiohttp_client: ClientSessionGenerator, socket_enabled: None) -> ClientSessionGenerator:
    """Return aiohttp_client and allow opening sockets."""
    return aiohttp_client


@pytest.fixture
def snapshot(snapshot: SnapshotAssertion) -> SnapshotAssertion:
    """Return snapshot assertion fixture with the Home Assistant extension."""
    return snapshot.use_extension(HomeAssistantSnapshotExtension)


@pytest.fixture
def config_entry_direct(hass_admin_user: User) -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        version=ConfigFlowHandler.VERSION,
        data={CONF_CONNECTION_TYPE: ConnectionType.DIRECT, CONF_PLATFORM: SmartHomePlatform.YANDEX},
        options={
            CONF_FILTER_SOURCE: EntityFilterSource.CONFIG_ENTRY,
            CONF_FILTER: {entityfilter.CONF_INCLUDE_ENTITY_GLOBS: ["*"]},
            CONF_SKILL: {
                CONF_USER_ID: hass_admin_user.id,
                CONF_ID: "foo",
                CONF_TOKEN: "token",
            },
        },
    )


@pytest.fixture()
def config_entry_cloud() -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        version=ConfigFlowHandler.VERSION,
        data={
            CONF_CONNECTION_TYPE: ConnectionType.CLOUD,
            CONF_CLOUD_INSTANCE: {
                CONF_CLOUD_INSTANCE_ID: "i-test",
                CONF_CLOUD_INSTANCE_CONNECTION_TOKEN: "token-foo",
            },
        },
        options={
            CONF_FILTER_SOURCE: EntityFilterSource.CONFIG_ENTRY,
            CONF_FILTER: {entityfilter.CONF_INCLUDE_ENTITY_GLOBS: ["*"]},
        },
    )


@pytest.fixture
def hass_platform(hass: HomeAssistant) -> HomeAssistant:
    demo_sensor = DemoSensor(
        "outside_temp",
        "Outside Temperature",
        state=15.6,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        unit_of_measurement=UnitOfTemperature.CELSIUS,
        battery=None,
    )
    demo_sensor.hass = hass
    demo_sensor.entity_id = "sensor.outside_temp"
    demo_sensor._attr_name = "Температура за бортом"  # type: ignore[assignment]

    demo_binary_sensor = DemoBinarySensor(
        "front_door",
        "Front Door",
        state=True,
        device_class=BinarySensorDeviceClass.DOOR,
    )
    demo_binary_sensor.hass = hass
    demo_binary_sensor.entity_id = "binary_sensor.front_door"
    demo_binary_sensor._attr_name = "Front Door"  # type: ignore[assignment]

    demo_light = DemoLight(
        "light_kitchen",
        "Kitchen Light",
        available=True,
        state=True,
    )
    demo_light.hass = hass
    demo_light.entity_id = "light.kitchen"
    demo_light._attr_name = "Kitchen Light"  # type: ignore[assignment]
    demo_light._ct = 240

    demo_sensor.async_write_ha_state()
    demo_binary_sensor.async_write_ha_state()
    demo_light.async_write_ha_state()

    return hass


@pytest.fixture
def hass_platform_direct(
    hass_platform: HomeAssistant, event_loop: asyncio.AbstractEventLoop, config_entry_direct: MockConfigEntry
) -> HomeAssistant:
    config_entry_direct.add_to_hass(hass_platform)
    event_loop.run_until_complete(hass_platform.config_entries.async_setup(config_entry_direct.entry_id))
    event_loop.run_until_complete(hass_platform.async_block_till_done())

    return hass_platform
