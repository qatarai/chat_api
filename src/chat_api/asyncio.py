"""Asyncio scheduling utilities for transport implementations.

Provides a small mixin to schedule coroutine sends and manage/get an event loop.
"""

from __future__ import annotations

import asyncio
import threading
from typing import Any, Coroutine, Optional


class AsyncioMixin:
    """Mixin that provides helpers to schedule coroutines from sync methods.

    Attempts to schedule work on a provided loop if available; otherwise uses
    the running loop or starts a private background loop if necessary.
    """

    def __init__(
        self, loop: Optional[asyncio.AbstractEventLoop] = None
    ) -> None:
        self._loop = loop

    def ensure_loop(self) -> asyncio.AbstractEventLoop:
        """Ensure there is an event loop to schedule tasks on.

        Returns the provided loop if running, else the current running loop,
        else spins up a new background loop thread and returns it.
        """
        # If the stored loop is running, return it.
        if self._loop is not None and self._loop.is_running():
            return self._loop

        # If there is a running loop, return it.
        try:
            return asyncio.get_running_loop()

        # If there is no running loop, create a new one.
        except RuntimeError:
            self._loop = asyncio.new_event_loop()

            def _run() -> None:
                if self._loop is not None:
                    self._loop.run_forever()
                else:
                    raise RuntimeError("No loop to run")

            t = threading.Thread(target=_run, daemon=True)
            t.start()
            return self._loop

    def run_coroutine(self, coro: Coroutine[Any, Any, None]) -> asyncio.Task:
        """Schedule a coroutine to run thread-safely on the target loop."""
        self.ensure_loop()
        return asyncio.create_task(coro)
