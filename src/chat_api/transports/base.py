"""Abstract transport interfaces."""

import logging
from abc import ABC, abstractmethod
from queue import Queue as ThreadQueue
from threading import Thread

from chat_api.exceptions import ChatApiTransportException
from chat_api.models import Event, InputMedia, OutputMedia
from chat_api.parsing import parse_bytes_event, parse_text_event

log = logging.getLogger("[ChatAPI:Transport]")


class Transport(ABC):
    """Transport interface.

    This transport is responsible for sending and receiving events
    to and from the other side of the connection.
    """

    def __init__(self, is_client: bool = False) -> None:
        self.send_queue = ThreadQueue[Event | None]()
        self.receive_queue = ThreadQueue[Event | None]()

        self.send_thread = Thread(target=self.run_send)
        self.receive_thread = Thread(target=self.run_receive)
        self.send_thread.start()
        self.receive_thread.start()

        self.is_client = is_client

    def send(self, event: Event) -> None:
        """Send an event to the other side of the connection."""
        log.debug("[Sending] Queuing %r", event)
        self.send_queue.put(event)
        log.debug("[Sending] Queued %r", event)

    @abstractmethod
    def send_impl(self, data: str | bytes) -> bool | Exception | None:
        """Send a message to the other side of the connection."""
        raise NotImplementedError()

    def run_send(self) -> None:
        """Run the send loop."""
        while True:
            event = self.send_queue.get()
            if event is None:
                log.debug("[Sending] Terminating send loop")
                break

            log.debug("[Sending] Sending %r", event)
            result = self.send_impl(
                event.get_bytes()
                if isinstance(event, (InputMedia, OutputMedia))
                else event.model_dump_json()
            )

            if isinstance(result, Exception):
                log.error("[Sending] Error while sending %r: %s", event, result)
            elif result is None:
                log.error("[Sending] Connection closed while sending %r", event)
                log.debug("[Sending] Terminating send loop")
                break
            else:
                log.debug("[Sending] Sent %r", event)

            self.send_queue.task_done()

        log.debug("[Sending] Terminated send loop")

    def receive(self) -> Event | None:
        """Receive an event from the other side of the connection.

        IMPORTANT: Return None after the last event.
        """
        event = self.receive_queue.get()
        log.debug("[Receiving] Received %r", event)
        self.receive_queue.task_done()

        return event

    @abstractmethod
    def receive_impl(self) -> str | bytes | None:
        """Receive a message from the other side of the connection."""
        raise NotImplementedError()

    def run_receive(self) -> None:
        """Run the receive loop."""
        while True:
            data = self.receive_impl()
            if data is None:
                log.debug("[Receiving] Terminating receive loop")
                self.receive_queue.put(None)
                break

            if isinstance(data, bytes):
                log.debug("[Receiving] Received %r bytes", len(data))
                log.debug("[Receiving] Parsing %r bytes", len(data))
            else:
                log.debug("[Receiving] Received %r", data)
                log.debug("[Receiving] Parsing %r", data)

            event = self.parse_event(data)
            log.debug("[Receiving] Parsed %r", event)

            log.debug("[Receiving] Queuing %r", event)
            self.receive_queue.put(event)
            log.debug("[Receiving] Queued %r", event)

        log.debug("[Receiving] Terminated receive loop")

    def parse_event(
        self,
        data: str | bytes,
    ) -> Event:
        """Parse the event from the data."""
        if isinstance(data, str):
            return parse_text_event(data)
        elif isinstance(data, bytes):
            return parse_bytes_event(
                data,
                parse_media_uuid=self.is_client,
            )
        else:
            raise ChatApiTransportException(f"Unknown message type: {type(data)}")

    def wait_for_send(self) -> None:
        """Wait for the send queue to be empty."""
        log.debug("[Sending] Blocking until all events are sent")
        self.send_queue.join()
        log.debug("[Sending] Unblocked after all events are sent")

    def close(self) -> None:
        """Close the transport."""
        log.debug("Closing the transport")
        self.send_queue.put(None)

    def join(self) -> None:
        """Join the transport."""
        log.debug("Blocking until the transport is closed")
        self.send_thread.join()
        self.receive_thread.join()
        log.debug("Unblocked after the transport is closed")
