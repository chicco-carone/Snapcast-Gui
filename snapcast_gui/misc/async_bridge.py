"""
Async Bridge module for integrating python-snapcast async callbacks with PySide6 Qt signals.

This module provides a singleton AsyncBridge class that:
1. Manages the shared asyncio event loop (via qasync)
2. Emits Qt signals when python-snapcast fires callbacks
3. Provides helper methods for running coroutines from Qt slots
"""

import asyncio
import logging
from typing import Optional, Any, Callable, Coroutine

from PySide6.QtCore import QObject, Signal


class AsyncBridge(QObject):
    """
    Bridge between python-snapcast async callbacks and PySide6 Qt signals.

    This class provides:
    - Qt signals for all python-snapcast events (client updates, server events, etc.)
    - Safe methods to schedule coroutines from the Qt thread
    - Callback handlers to connect to python-snapcast objects

    Usage:
        bridge = AsyncBridge.instance()
        bridge.client_volume_changed.connect(my_slot)
        bridge.schedule_coroutine(some_async_function())
    """

    _instance: Optional["AsyncBridge"] = None

    # Server-level signals
    server_connected = Signal(object)  # Emits server object
    server_disconnected = Signal()
    server_updated = Signal(object)  # Emits server object

    # Client-level signals
    client_connected = Signal(str)  # Emits client identifier
    client_disconnected = Signal(str)  # Emits client identifier
    client_updated = Signal(str, object)  # Emits (client_id, client object)
    client_volume_changed = Signal(str, int)  # Emits (client_id, volume)
    client_mute_changed = Signal(str, bool)  # Emits (client_id, muted)
    client_name_changed = Signal(str, str)  # Emits (client_id, new_name)

    group_updated = Signal(str, object)  # Emits (group_id, group object)
    group_mute_changed = Signal(str, bool)  # Emits (group_id, muted)
    group_stream_changed = Signal(str, str)  # Emits (group_id, stream_id)
    # Stream-level signals
    stream_updated = Signal(str, object)  # Emits (stream_id, stream object)

    async_error = Signal(str, str)  # Emits (operation_name, error_message)

    def __init__(self, log_level: int = logging.INFO):
        super().__init__()
        self.logger = logging.getLogger("AsyncBridge")
        self.logger.setLevel(log_level)
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._server = None
        self._client_connected_state: dict = {}

    @classmethod
    def instance(cls, log_level: int = logging.INFO) -> "AsyncBridge":
        """Get the singleton instance of AsyncBridge."""
        if cls._instance is None:
            cls._instance = cls(log_level)
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance (useful for testing)."""
        cls._instance = None

    def set_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Set the asyncio event loop (should be the qasync loop)."""
        self._loop = loop
        self.logger.debug("Event loop set in AsyncBridge")

    def get_event_loop(self) -> Optional[asyncio.AbstractEventLoop]:
        """Get the current event loop."""
        return self._loop

    @property
    def server(self):
        """Get the current server object."""
        return self._server

    @server.setter
    def server(self, value):
        """Set the server and register callbacks."""
        self._server = value
        if value is not None:
            self._register_server_callbacks(value)

    def _register_server_callbacks(self, server) -> None:
        """Register all python-snapcast callbacks on the server object."""
        self.logger.debug("Registering server callbacks")

        # Server-level callbacks
        server.set_on_update_callback(self._on_server_update)
        server.set_on_connect_callback(self._on_server_connect)
        server.set_on_disconnect_callback(self._on_server_disconnect)
        server.set_new_client_callback(self._on_new_client)

        # Register callbacks on existing clients, groups, and streams
        for client in server.clients:
            self._register_client_callback(client)

        for group in server.groups:
            self._register_group_callback(group)

        for stream in server.streams:
            self._register_stream_callback(stream)

    def _register_client_callback(self, client) -> None:
        """Register callback on a single client."""
        # Store initial connection state
        self._client_connected_state[client.identifier] = client.connected
        client.set_callback(lambda c=client: self._on_client_update(c))
        self.logger.debug(
            f"Registered callback for client {client.identifier}, connected: {client.connected}"
        )

    def _register_group_callback(self, group) -> None:
        """Register callback on a single group."""
        group.set_callback(lambda g=group: self._on_group_update(g))
        self.logger.debug(f"Registered callback for group {group.identifier}")

    def _register_stream_callback(self, stream) -> None:
        """Register callback on a single stream."""
        stream.set_callback(lambda s=stream: self._on_stream_update(s))
        self.logger.debug(f"Registered callback for stream {stream.identifier}")

    # ==================== Server Callbacks ====================

    def _on_server_connect(self) -> None:
        """Called when connection to server is established."""
        self.logger.info("Server connected callback triggered")
        self.server_connected.emit(self._server)

    def _on_server_disconnect(self, exception: Optional[Exception] = None) -> None:
        """Called when disconnected from server."""
        self.logger.info(f"Server disconnected callback triggered: {exception}")
        self.server_disconnected.emit()

    def _on_server_update(self) -> None:
        """Called when server state is updated."""
        self.logger.debug("Server update callback triggered")
        if self._server:
            # Re-register callbacks for any new clients/groups/streams
            for client in self._server.clients:
                self._register_client_callback(client)
            for group in self._server.groups:
                self._register_group_callback(group)
            for stream in self._server.streams:
                self._register_stream_callback(stream)

            self.server_updated.emit(self._server)

    def _on_new_client(self, client) -> None:
        """Called when a new client connects to the server."""
        self.logger.info(f"New client connected: {client.identifier}")
        self._register_client_callback(client)
        self.client_connected.emit(client.identifier)

    # ==================== Client Callbacks ====================

    def _on_client_update(self, client) -> None:
        """Called when a client's state changes."""
        client_id = client.identifier
        was_connected = self._client_connected_state.get(client_id, False)
        is_connected = client.connected

        self.logger.debug(
            f"Client update callback for {client_id}: was_connected={was_connected}, is_connected={is_connected}"
        )

        # Track state change
        self._client_connected_state[client_id] = is_connected

        if is_connected and not was_connected:
            self.logger.info(f"Client {client_id} came online")
            self.client_connected.emit(client_id)
        elif not is_connected and was_connected:
            self.logger.info(f"Client {client_id} went offline")
            self.client_disconnected.emit(client_id)

        self.client_updated.emit(client_id, client)

    # ==================== Group Callbacks ====================

    def _on_group_update(self, group) -> None:
        """Called when a group's state changes."""
        self.logger.debug(f"Group update callback for {group.identifier}")
        self.group_updated.emit(group.identifier, group)

    # ==================== Stream Callbacks ====================

    def _on_stream_update(self, stream) -> None:
        """Called when a stream's state changes."""
        self.logger.debug(f"Stream update callback for {stream.identifier}")
        self.stream_updated.emit(stream.identifier, stream)

    # ==================== Async Helpers ====================

    def schedule_coroutine(
        self,
        coro: Coroutine,
        callback: Optional[Callable[[Any], None]] = None,
        error_callback: Optional[Callable[[Exception], None]] = None,
    ) -> Optional[asyncio.Task]:
        """
        Schedule a coroutine to run in the event loop.

        Args:
            coro: The coroutine to run
            callback: Optional callback to receive the result
            error_callback: Optional callback to receive any exception

        Returns:
            The created Task, or None if no loop is available
        """
        if self._loop is None:
            self.logger.error("Cannot schedule coroutine: no event loop set")
            return None

        async def wrapped_coro():
            try:
                result = await coro
                if callback:
                    callback(result)
                return result
            except Exception as e:
                self.logger.error(f"Error in scheduled coroutine: {e}")
                if error_callback:
                    error_callback(e)
                else:
                    self.async_error.emit("coroutine", str(e))
                raise

        task = asyncio.ensure_future(wrapped_coro(), loop=self._loop)
        return task

    def run_coroutine_sync(self, coro: Coroutine) -> Any:
        """
        Run a coroutine synchronously (blocking).

        WARNING: This blocks the Qt event loop and should only be used
        for quick operations during initialization or cleanup.

        Args:
            coro: The coroutine to run

        Returns:
            The result of the coroutine
        """
        if self._loop is None:
            raise RuntimeError("No event loop set in AsyncBridge")

        return self._loop.run_until_complete(coro)

    def clear_server(self) -> None:
        """Clear the server reference (on disconnect)."""
        self._server = None
        self._client_connected_state.clear()
        self.logger.debug("Server cleared from AsyncBridge")
