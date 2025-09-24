"""Asyncio scheduling utilities for transport implementations.

Provides a small mixin to schedule coroutine sends and manage/get an event loop.
"""

from __future__ import annotations

import asyncio
import threading
from typing import Any, Coroutine, Optional


class AsyncioSchedulingMixin:
    """Mixin that provides helpers to schedule coroutines from sync methods.

    Attempts to schedule work on a provided loop if available; otherwise uses
    the running loop or starts a private background loop if necessary.
    """

    _loop: Optional[asyncio.AbstractEventLoop]

    def _ensure_loop(self) -> asyncio.AbstractEventLoop:
        """Ensure there is an event loop to schedule tasks on.

        Returns the provided loop if running, else the current running loop,
        else spins up a new background loop thread and returns it.
        """
        loop = getattr(self, "_loop", None)
        if loop is not None and loop.is_running():
            return loop
        try:
            return asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            self._loop = loop

            def _run() -> None:
                loop.run_forever()

            t = threading.Thread(target=_run, daemon=True)
            t.start()
            return loop

    def _schedule_send(self, coro: Coroutine[Any, Any, None]) -> None:
        """Schedule a coroutine to run thread-safely on the target loop."""
        loop = self._ensure_loop()
        asyncio.run_coroutine_threadsafe(coro, loop)
