"""Yandex Smart Home HTTP interface."""
import logging
from typing import Any, Awaitable, Callable, Coroutine, TypeVar, cast

from aiohttp.web import HTTPServiceUnavailable, Request, Response, json_response
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant, callback

from . import handlers
from .const import CONFIG, DOMAIN
from .helpers import Config, RequestData
from .schema import DeviceList

_LOGGER = logging.getLogger(__name__)
_T = TypeVar("_T", bound=HomeAssistantView)


@callback
def async_register_http(hass: HomeAssistant) -> None:
    """Register HTTP views for Yandex Smart Home."""
    hass.http.register_view(YandexSmartHomeUnauthorizedView())
    hass.http.register_view(YandexSmartHomePingView())
    hass.http.register_view(YandexSmartHomeView())


def async_http_request(
    func: Callable[[_T, HomeAssistant, Request, RequestData], Awaitable[Response]]
) -> Callable[[_T, Request], Coroutine[Any, Any, Response]]:
    """Decorate an async function to handle HTTP requests."""

    async def _log_request(request: Request) -> None:
        """Log the request."""
        if body := await request.text():
            _LOGGER.debug(f"Request: {request.url} ({request.method} data: {body})")
        else:
            _LOGGER.debug(f"Request: {request.url} ({request.method})")

    async def decorator(self: _T, request: Request) -> Response:
        """Decorate."""
        await _log_request(request)
        hass: HomeAssistant = request.app["hass"]
        config: Config | None = hass.data[DOMAIN][CONFIG]
        context = self.context(request)
        if config is None:
            raise HTTPServiceUnavailable(text="Error: Integration is not enabled")
        if not config.is_direct_connection:
            raise HTTPServiceUnavailable(text="Error: Integration uses cloud connection")

        data = RequestData(
            config=config,
            context=context,
            request_user_id=context.user_id,
            request_id=request.headers.get("X-Request-Id"),
        )

        return await func(self, hass, request, data)

    return decorator


class YandexSmartHomeUnauthorizedView(HomeAssistantView):
    """View to handle Yandex Smart Home unauthorized HTTP requests."""

    url = f"/api/{DOMAIN}/v1.0"
    name = f"api:{DOMAIN}:unauthorized"
    requires_auth = False

    @async_http_request
    async def head(self, _: HomeAssistant, __: Request, ___: RequestData) -> Response:
        """Handle Yandex Smart Home HEAD requests."""
        print(123)
        return Response(status=200)


class YandexSmartHomePingView(HomeAssistantView):
    """View to handle Yandex Smart Home ping requests."""

    url = f"/api/{DOMAIN}/v1.0/ping"
    name = f"api:{DOMAIN}:unauthorized"
    requires_auth = False

    @async_http_request
    async def get(self, hass: HomeAssistant, _request: Request, data: RequestData) -> Response:
        """Handle Yandex Smart Home GET requests."""
        data.request_user_id = "ping"
        dl = cast(DeviceList, await handlers.async_device_list(hass, data, ""))
        return Response(text=f"OK: {len(dl.devices)}", status=200)


class YandexSmartHomeView(YandexSmartHomeUnauthorizedView):
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
        result = await handlers.async_handle_request(
            hass, data, action=request.path.replace(self.url, "", 1), payload=await request.text()
        )
        response = json_response(text=result.json(exclude_none=True))
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
