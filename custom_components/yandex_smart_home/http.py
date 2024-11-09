"""The Yandex Smart Home HTTP interface."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Coroutine, TypeVar

from aiohttp.web import HTTPServiceUnavailable, Request, Response, json_response
from homeassistant.components.http import KEY_HASS, KEY_HASS_REFRESH_TOKEN_ID, HomeAssistantView
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import issue_registry as ir

from . import DOMAIN, handlers
from .const import ISSUE_ID_MISSING_INTEGRATION
from .helpers import RequestData, SmartHomePlatform

if TYPE_CHECKING:
    from . import YandexSmartHome

_LOGGER = logging.getLogger(__name__)
_T = TypeVar("_T", bound="YandexSmartHomeView")


async def _log_request(request: Request) -> None:
    """Log the request."""
    if body := await request.text():
        _LOGGER.debug(f"Request: {request.url} ({request.method} data: {body})")
    else:
        _LOGGER.debug(f"Request: {request.url} ({request.method})")


@callback
def async_register_http(hass: HomeAssistant, component: YandexSmartHome) -> None:
    """Register HTTP views for Yandex Smart Home."""
    hass.http.register_view(YandexSmartHomeUnauthorizedView(component))
    return hass.http.register_view(YandexSmartHomeAPIView(component))


def async_http_request(
    func: Callable[[_T, HomeAssistant, Request, RequestData], Awaitable[Response]]
) -> Callable[[_T, Request], Coroutine[Any, Any, Response]]:
    """Decorate an async function to handle authorized HTTP requests."""

    async def decorator(self: _T, request: Request) -> Response:
        """Decorate."""
        await _log_request(request)

        hass: HomeAssistant = request.app[KEY_HASS]
        context = self.context(request)

        refresh_token = hass.auth.async_get_refresh_token(request[KEY_HASS_REFRESH_TOKEN_ID])
        assert refresh_token is not None

        platform = SmartHomePlatform.from_client_id(refresh_token.client_id or "")
        if not platform:
            _LOGGER.error(f"Request from unsupported platform, client_id: {refresh_token.client_id}")
            raise HTTPServiceUnavailable()

        entry_data = self._component.get_direct_connection_entry_data(platform, refresh_token.user.id)
        if not entry_data and len(hass.config_entries.async_entries(DOMAIN)) == 1:
            # backward compatibility
            entry_data = self._component.get_direct_connection_entry_data(platform, None)

        issue_id = f"{ISSUE_ID_MISSING_INTEGRATION}_{platform}_{refresh_token.user.id}"
        if not entry_data:
            _LOGGER.error(
                f"Failed to find Yandex Smart Home integration for request "
                f"from {platform} (user {refresh_token.user.name})"
            )
            ir.async_create_issue(
                hass,
                DOMAIN,
                issue_id,
                is_fixable=False,
                severity=ir.IssueSeverity.ERROR,
                translation_key=ISSUE_ID_MISSING_INTEGRATION,
                translation_placeholders={
                    "platform": platform,
                    "username": refresh_token.user.name or refresh_token.user.id,
                },
            )
            raise HTTPServiceUnavailable()
        else:
            ir.async_delete_issue(hass, DOMAIN, issue_id)

        data = RequestData(
            entry_data=entry_data,
            context=context,
            platform=platform,
            request_user_id=context.user_id,
            request_id=request.headers.get("X-Request-Id"),
        )
        if entry_data.skill:
            data.request_user_id = entry_data.skill.user_id

        return await func(self, hass, request, data)

    return decorator


class YandexSmartHomeView(HomeAssistantView):
    def __init__(self, component: YandexSmartHome):
        self._component = component


class YandexSmartHomeUnauthorizedView(YandexSmartHomeView):
    """View to handle Yandex Smart Home unauthorized HTTP requests."""

    url = f"/api/{DOMAIN}/v1.0"
    extra_urls = [
        url + "/ping",
    ]
    name = f"api:{DOMAIN}:unauthorized"
    requires_auth = False

    @staticmethod
    async def head(request: Request) -> Response:
        """Handle Yandex Smart Home HEAD requests."""
        await _log_request(request)
        return Response(status=200)

    @staticmethod
    async def get(request: Request) -> Response:
        """Handle Yandex Smart Home GET requests."""
        await _log_request(request)
        return Response(text="Yandex Smart Home", status=200)


class YandexSmartHomeAPIView(YandexSmartHomeView):
    """View to handle Yandex Smart Home HTTP requests."""

    url = f"/api/{DOMAIN}/v1.0"
    extra_urls = [
        url + "/user/unlink",
        url + "/user/devices",
        url + "/user/devices/query",
        url + "/user/devices/action",
    ]
    name = f"api:{DOMAIN}"
    requires_auth = True

    async def _async_handle_request(self, hass: HomeAssistant, request: Request, data: RequestData) -> Response:
        """Handle Yandex Smart Home requests."""
        assert self.url is not None
        result = await handlers.async_handle_request(
            hass, data, action=request.path.replace(self.url, "", 1), payload=await request.text()
        )
        response = json_response(text=result.as_json())
        _LOGGER.debug(f"Response: {response.text}")

        return response

    @async_http_request
    async def post(self, hass: HomeAssistant, request: Request, data: RequestData) -> Response:
        """Handle Yandex Smart Home POST requests."""
        return await self._async_handle_request(hass, request, data)

    @async_http_request
    async def get(self, hass: HomeAssistant, request: Request, data: RequestData) -> Response:
        """Handle Yandex Smart Home GET requests."""
        return await self._async_handle_request(hass, request, data)
