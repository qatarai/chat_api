"""Abstract transport interfaces."""

import logging
from abc import ABC, abstractmethod
from queue import Queue as ThreadQueue
from threading import Thread

from chat_api.exceptions import ChatApiTransportException
from chat_api.models import Event, InputMedia, OutputMedia
from chat_api.parsing import parse_bytes_event, parse_text_event

log = logging.getLogger(__name__)


class Transport(ABC):
    """Transport interface.

    This transport is responsible for sending and receiving events
    to and from the other side of the connection.
    """

    def __init__(self, is_client: bool = False) -> None:
        self.send_queue = ThreadQueue[Event | None]()
        self.receive_queue = ThreadQueue[Event | None]()

        self.send_thread = Thread(target=self.run_send, daemon=True)
        self.receive_thread = Thread(target=self.run_receive, daemon=True)
        self.send_thread.start()
        self.receive_thread.start()

        self.is_client = is_client

    def send(self, event: Event) -> None:
        """Send an event to the other side of the connection."""
        if isinstance(event, (InputMedia, OutputMedia)):
            log.debug("Queueing media event with size: %s", len(event.data))
        else:
            log.debug("Queueing event: %s", event)

        self.send_queue.put(event)

    @abstractmethod
    def send_impl(self, data: str | bytes) -> None:
        """Send a message to the other side of the connection."""
        raise NotImplementedError()

    def run_send(self) -> None:
        """Run the send loop."""
        while True:
            event = self.send_queue.get()
            if event is None:
                break

            if isinstance(event, (InputMedia, OutputMedia)):
                log.debug("Sending media event with size: %s", len(event.data))
            else:
                log.debug("Sending event: %s", event)

            self.send_impl(
                event.get_bytes()
                if isinstance(event, (InputMedia, OutputMedia))
                else event.model_dump_json()
            )

            self.send_queue.task_done()

        log.debug("Send loop terminated")

    def receive(self) -> Event | None:
        """Receive an event from the other side of the connection.

        IMPORTANT: Return None after the last event.
        """
        event = self.receive_queue.get()
        self.receive_queue.task_done()

        if isinstance(event, (InputMedia, OutputMedia)):
            log.debug("Unqueued media event with size: %s", len(event.data))
        else:
            log.debug("Unqueued event: %s", event)

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
                self.receive_queue.put(None)
                break

            if isinstance(data, bytes):
                log.debug("Received bytes data with size: %s", len(data))
            else:
                log.debug("Received text data: %s", data)

            event = self.parse_event(data)
            self.receive_queue.put(event)

        log.debug("Receive loop terminated")

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
        log.debug("Waiting for send queue to be empty")
        self.send_queue.join()
        log.debug("Send queue is empty")

    def close(self) -> None:
        """Close the transport."""
        log.debug("Closing")
        self.send_queue.put(None)

    def join(self) -> None:
        """Join the transport."""
        log.debug("Joining to wait closing")
        self.send_thread.join()
        self.receive_thread.join()
        log.debug("Closed")
