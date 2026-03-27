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

    Receives JSON POST data from one or more Nedap PowerRouters on /logs.json
    and distributes it via registered callbacks. Each PowerRouter is identified
    by its unique ``powerrouter_id`` in the JSON header.

    Optionally forwards the raw data to the real Nedap server.
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

        # General callbacks – receive ALL data regardless of device
        self._callbacks: list[Callable[[dict[str, Any]], None]] = []

        # Per-device callbacks – only receive data for a specific powerrouter_id
        self._device_callbacks: dict[
            str, list[Callable[[dict[str, Any]], None]]
        ] = {}

        # Callback fired when a previously unseen powerrouter_id is discovered
        self._discovery_callbacks: list[Callable[[str], None]] = []

        # Set of known powerrouter_ids
        self._known_devices: set[str] = set()

    @property
    def known_devices(self) -> set[str]:
        """Return the set of discovered powerrouter_ids."""
        return self._known_devices.copy()

    # ── General callbacks (all data) ──────────────────────────────

    def register_callback(
        self, callback: Callable[[dict[str, Any]], None]
    ) -> None:
        """Register a callback that receives ALL incoming data."""
        self._callbacks.append(callback)

    def remove_callback(
        self, callback: Callable[[dict[str, Any]], None]
    ) -> None:
        """Remove a general callback."""
        try:
            self._callbacks.remove(callback)
        except ValueError:
            _LOGGER.debug("Callback not found for removal, ignoring")

    # ── Per-device callbacks ──────────────────────────────────────

    def register_device_callback(
        self,
        powerrouter_id: str,
        callback: Callable[[dict[str, Any]], None],
    ) -> None:
        """Register a callback for a specific powerrouter_id."""
        self._device_callbacks.setdefault(powerrouter_id, []).append(callback)

    def remove_device_callback(
        self,
        powerrouter_id: str,
        callback: Callable[[dict[str, Any]], None],
    ) -> None:
        """Remove a per-device callback."""
        cbs = self._device_callbacks.get(powerrouter_id, [])
        try:
            cbs.remove(callback)
        except ValueError:
            _LOGGER.debug(
                "Device callback not found for %s, ignoring", powerrouter_id
            )

    # ── Discovery callbacks ───────────────────────────────────────

    def register_discovery_callback(
        self, callback: Callable[[str], None]
    ) -> None:
        """Register a callback fired when a new powerrouter_id is seen.

        The callback receives the powerrouter_id string as its argument.
        """
        self._discovery_callbacks.append(callback)

    def remove_discovery_callback(
        self, callback: Callable[[str], None]
    ) -> None:
        """Remove a discovery callback."""
        try:
            self._discovery_callbacks.remove(callback)
        except ValueError:
            pass

    # ── Server lifecycle ──────────────────────────────────────────

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

    # ── Request handlers ──────────────────────────────────────────

    async def _forward_to_real_server(self, raw_body: bytes) -> None:
        """Forward the raw POST body to the real logging1.powerrouter.com."""
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
        """Handle POST /logs.json from one or more PowerRouters."""
        try:
            raw_body = await request.read()
            data: dict[str, Any] = json.loads(raw_body)

            # Extract powerrouter_id from header
            header = data.get("header", {})
            pr_id: str = header.get("powerrouter_id", "unknown")

            _LOGGER.debug(
                "Received data from PowerRouter %s: %s",
                pr_id,
                json.dumps(data, indent=2),
            )

            # Discover new devices
            if pr_id != "unknown" and pr_id not in self._known_devices:
                self._known_devices.add(pr_id)
                _LOGGER.info(
                    "New PowerRouter discovered: %s (total: %d)",
                    pr_id,
                    len(self._known_devices),
                )
                for cb in self._discovery_callbacks:
                    try:
                        cb(pr_id)
                    except Exception:
                        _LOGGER.exception("Error in discovery callback")

            # Fire general callbacks (all data)
            for cb in self._callbacks:
                try:
                    cb(data)
                except Exception:
                    _LOGGER.exception("Error in data callback")

            # Fire per-device callbacks
            if pr_id in self._device_callbacks:
                for cb in self._device_callbacks[pr_id]:
                    try:
                        cb(data)
                    except Exception:
                        _LOGGER.exception(
                            "Error in device callback for %s", pr_id
                        )

            # Forward to real server (fire-and-forget, non-blocking)
            if self._forward_enabled and self._session:
                asyncio.create_task(self._forward_to_real_server(raw_body))

            return web.json_response({"status": "ok"})

        except json.JSONDecodeError:
            _LOGGER.warning("Received non-JSON data from PowerRouter")
            return web.Response(status=400, text="Invalid JSON")
        except Exception:
            _LOGGER.exception("Error processing PowerRouter data")
            return web.Response(status=500, text="Internal error")

    async def _handle_catchall(self, request: web.Request) -> web.Response:
        """Handle all other requests."""
        body = await request.read()
        _LOGGER.debug(
            "PowerRouter catchall: %s %s (body: %s bytes)",
            request.method,
            request.path,
            len(body),
        )
        return web.Response(status=200, text="OK")
