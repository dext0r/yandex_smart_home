"""Global fixtures for yandex_smart_home integration."""
from unittest.mock import patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.yandex_smart_home import DOMAIN, const

pytest_plugins = 'pytest_homeassistant_custom_component'


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


@pytest.fixture
def config_entry():
    return MockConfigEntry(domain=DOMAIN)


@pytest.fixture
def config_entry_with_notifier(hass_admin_user):
    return MockConfigEntry(domain=DOMAIN, data={const.CONF_NOTIFIER: [{
        const.CONF_NOTIFIER_OAUTH_TOKEN: '',
        const.CONF_NOTIFIER_SKILL_ID: '',
        const.CONF_NOTIFIER_USER_ID: hass_admin_user.id,
    }]})


@pytest.fixture(name='skip_notifications', autouse=True)
def skip_notifications_fixture():
    """Skip notification calls."""
    with patch('homeassistant.components.persistent_notification.async_create'), patch(
        'homeassistant.components.persistent_notification.async_dismiss'
    ):
        yield
