"""Support for Yandex Smart Home."""
from __future__ import annotations
import logging
from typing import Any

from aiohttp.web import Request, Response
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import callback

from .const import DOMAIN, CONFIG
from .smart_home import async_handle_message

_LOGGER = logging.getLogger(__name__)


@callback
def async_register_http(hass):
    """Register HTTP views for Yandex Smart Home."""
    hass.http.register_view(YandexSmartHomeUnauthorizedView())
    hass.http.register_view(YandexSmartHomeView())


class YandexSmartHomeUnauthorizedView(HomeAssistantView):
    """Handle Yandex Smart Home unauthorized requests."""

    url = '/api/yandex_smart_home/v1.0'
    name = 'api:yandex_smart_home:unauthorized'
    requires_auth = False

    # noinspection PyMethodMayBeStatic
    async def head(self, request: Request) -> Response:
        """Handle Yandex Smart Home HEAD requests."""
        _LOGGER.debug('Request: %s (HEAD)' % request.url)

        if not request.app['hass'].data[DOMAIN][CONFIG]:
            _LOGGER.debug('Integation is not enabled')
            return Response(status=404)

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

    async def _async_handle_request(self, request: Request, message: dict[str, Any]) -> Response:
        if not request.app['hass'].data[DOMAIN][CONFIG]:
            _LOGGER.debug('Integation is not enabled')
            return Response(status=404)

        result = await async_handle_message(
            request.app['hass'],
            request.app['hass'].data[DOMAIN][CONFIG],
            request['hass_user'].id,
            request.headers.get('X-Request-Id'),
            request.path.replace(self.url, '', 1),
            message
        )

        response = self.json(result)
        _LOGGER.debug(f'Response: {response.text}')
        return response

    async def post(self, request: Request) -> Response:
        """Handle Yandex Smart Home POST requests."""
        _LOGGER.debug('Request: %s (POST data: %s)' % (request.url, await request.text()))
        return await self._async_handle_request(request, await request.json())

    async def get(self, request: Request) -> Response:
        """Handle Yandex Smart Home GET requests."""
        _LOGGER.debug('Request: %s' % request.url)
        return await self._async_handle_request(request, {})
