"""Support for Yandex Smart Home."""
import logging

from aiohttp.web import Request, Response

# Typing imports
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import callback
from homeassistant.const import CLOUD_NEVER_EXPOSED_ENTITIES

from .const import (
    CONF_EXPOSE_BY_DEFAULT,
    CONF_EXPOSED_DOMAINS,
    CONF_ENTITY_CONFIG,
    CONF_EXPOSE,
)
from .smart_home import async_handle_message
from .helpers import Config

_LOGGER = logging.getLogger(__name__)


@callback
def async_register_http(hass, cfg):
    """Register HTTP views for Yandex Smart Home."""
    expose_by_default = cfg.get(CONF_EXPOSE_BY_DEFAULT)
    exposed_domains = cfg.get(CONF_EXPOSED_DOMAINS)
    entity_config = cfg.get(CONF_ENTITY_CONFIG) or {}

    def is_exposed(entity) -> bool:
        """Determine if an entity should be exposed to Yandex Smart Home."""
        if entity.attributes.get('view') is not None:
            # Ignore entities that are views
            return False

        if entity.entity_id in CLOUD_NEVER_EXPOSED_ENTITIES:
            return False

        explicit_expose = \
            entity_config.get(entity.entity_id, {}).get(CONF_EXPOSE)

        domain_exposed_by_default = \
            expose_by_default and entity.domain in exposed_domains

        # Expose an entity if the entity's domain is exposed by default and
        # the configuration doesn't explicitly exclude it from being
        # exposed, or if the entity is explicitly exposed
        is_default_exposed = \
            domain_exposed_by_default and explicit_expose is not False

        return is_default_exposed or explicit_expose

    config = Config(
        should_expose=is_exposed,
        entity_config=entity_config
    )

    hass.http.register_view(YandexSmartHomeUnauthorizedView())
    hass.http.register_view(YandexSmartHomeView(config))

class YandexSmartHomeUnauthorizedView(HomeAssistantView):
    """Handle Yandex Smart Home unauthorized requests."""

    url = '/api/yandex_smart_home/v1.0'
    name = 'api:yandex_smart_home:unauthorized'
    requires_auth = False

    async def head(self, request: Request) -> Response:
        """Handle Yandex Smart Home HEAD requests."""
        _LOGGER.debug("Request: %s (HEAD)" % request.url)
        return Response(status=200)

class YandexSmartHomeView(YandexSmartHomeUnauthorizedView):
    """Handle Yandex Smart Home requests."""

    url = '/api/yandex_smart_home/v1.0'
    extra_urls = [
        url + '/user/unlink',
        url + '/user/devices',
        url + '/user/devices/query',
        url + '/user/devices/action',
    ]
    name = 'api:yandex_smart_home'
    requires_auth = True

    def __init__(self, config):
        """Initialize the Yandex Smart Home request handler."""
        self.config = config

    async def post(self, request: Request) -> Response:
        """Handle Yandex Smart Home POST requests."""
        message = await request.json()  # type: dict
        _LOGGER.debug("Request: %s (POST data: %s)" % (request.url,  message))
        result = await async_handle_message(
            request.app['hass'],
            self.config,
            request['hass_user'].id,
            request.headers.get('X-Request-Id'),
            request.path.replace(self.url, '', 1),
            message)
        _LOGGER.debug("Response: %s", result)
        return self.json(result)

    async def get(self, request: Request) -> Response:
        """Handle Yandex Smart Home GET requests."""
        _LOGGER.debug("Request: %s" % request.url)
        result = await async_handle_message(
             request.app['hass'],
             self.config,
             request['hass_user'].id,
             request.headers.get('X-Request-Id'),
             request.path.replace(self.url, '', 1),
             {})
        _LOGGER.debug("Response: %s" % result)
        return self.json(result)
