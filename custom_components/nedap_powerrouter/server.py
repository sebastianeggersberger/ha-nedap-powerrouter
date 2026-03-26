"""HTTP server to receive Nedap PowerRouter data."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Callable

import aiohttp
from aiohttp import web

from .const import FORWARD_HOST_HEADER, FORWARD_PATH, FORWARD_TIMEOUT_SECONDS

_LOGGER = logging.getLogger(__name__)


class PowerRouterHTTPServer:
    """HTTP server that mimics logging1.powerrouter.com.

    Receives JSON POST data from the Nedap PowerRouter on /logs.json
    and distributes it via registered callbacks. Optionally forwards
    the raw data to the real Nedap server.
    """

    def __init__(
        self,
        port: int = 8099,
        forward_enabled: bool = False,
        forward_ip: str = "",
    ) -> None:
        """Initialise the server."""
        self._port = port
        self._forward_enabled = forward_enabled
        self._forward_ip = forward_ip.strip()
        self._app = web.Application()
        self._app.router.add_post("/logs.json", self._handle_logs)
        self._app.router.add_route("*", "/{path:.*}", self._handle_catchall)
        self._runner: web.AppRunner | None = None
        self._session: aiohttp.ClientSession | None = None
        self._callbacks: list[Callable[[dict[str, Any]], None]] = []
        self._last_data: dict[str, Any] | None = None

    @property
    def last_data(self) -> dict[str, Any] | None:
        """Return the last received data."""
        return self._last_data

    def register_callback(
        self, callback: Callable[[dict[str, Any]], None]
    ) -> None:
        """Register a callback for new data."""
        self._callbacks.append(callback)

    def remove_callback(
        self, callback: Callable[[dict[str, Any]], None]
    ) -> None:
        """Remove a registered callback."""
        try:
            self._callbacks.remove(callback)
        except ValueError:
            _LOGGER.debug("Callback not found for removal, ignoring")

    async def start(self) -> None:
        """Start the HTTP server."""
        self._runner = web.AppRunner(self._app)
        await self._runner.setup()
        site = web.TCPSite(self._runner, "0.0.0.0", self._port)
        await site.start()
        _LOGGER.info(
            "PowerRouter HTTP server started on port %s", self._port
        )

        if self._forward_enabled and self._forward_ip:
            timeout = aiohttp.ClientTimeout(total=FORWARD_TIMEOUT_SECONDS)
            self._session = aiohttp.ClientSession(timeout=timeout)
            _LOGGER.info(
                "Forwarding enabled → http://%s%s",
                self._forward_ip,
                FORWARD_PATH,
            )
        else:
            _LOGGER.info("Forwarding to real server is disabled")

    async def stop(self) -> None:
        """Stop the HTTP server."""
        if self._session:
            await self._session.close()
            self._session = None
        if self._runner:
            await self._runner.cleanup()
            _LOGGER.info("PowerRouter HTTP server stopped")

    async def _forward_to_real_server(self, raw_body: bytes) -> None:
        """Forward the raw POST body to the real logging1.powerrouter.com.

        This runs as a fire-and-forget task so it does not delay the
        response back to the PowerRouter.
        """
        if not self._session or not self._forward_ip:
            return

        url = f"http://{self._forward_ip}{FORWARD_PATH}"
        headers = {
            "Host": FORWARD_HOST_HEADER,
            "Content-Type": "application/json",
        }

        try:
            async with self._session.post(
                url, data=raw_body, headers=headers
            ) as resp:
                _LOGGER.debug(
                    "Forwarded to %s → HTTP %s", url, resp.status
                )
        except TimeoutError:
            _LOGGER.warning("Forward to %s timed out", url)
        except Exception:
            _LOGGER.warning("Forward to %s failed", url, exc_info=True)

    async def _handle_logs(self, request: web.Request) -> web.Response:
        """Handle POST /logs.json from the PowerRouter.

        The PowerRouter sends JSON with this structure:
        {
          "header": {
            "powerrouter_id": "...",
            "time_send": "...",
            "version": 3,
            "period": 60
          },
          "module_statuses": [
            {
              "module_id": 16,
              "status": ...,
              "param_0": ...,
              ...
            }
          ]
        }
        """
        try:
            raw_body = await request.read()
            data: dict[str, Any] = json.loads(raw_body)
            _LOGGER.debug(
                "Received PowerRouter data: %s",
                json.dumps(data, indent=2),
            )
            self._last_data = data

            for cb in self._callbacks:
                try:
                    cb(data)
                except Exception:
                    _LOGGER.exception("Error in data callback")

            # Forward to real server (fire-and-forget, non-blocking)
            if self._forward_enabled and self._session:
                asyncio.create_task(self._forward_to_real_server(raw_body))

            # Return 200 OK so the PowerRouter is happy
            return web.json_response({"status": "ok"})

        except json.JSONDecodeError:
            _LOGGER.warning("Received non-JSON data from PowerRouter")
            return web.Response(status=400, text="Invalid JSON")
        except Exception:
            _LOGGER.exception("Error processing PowerRouter data")
            return web.Response(status=500, text="Internal error")

    async def _handle_catchall(self, request: web.Request) -> web.Response:
        """Handle all other requests.

        The PowerRouter may send other requests (e.g. status checks).
        We just respond 200 OK to keep it happy.
        """
        body = await request.read()
        _LOGGER.debug(
            "PowerRouter catchall: %s %s (body: %s bytes)",
            request.method,
            request.path,
            len(body),
        )
        return web.Response(status=200, text="OK")
