"""Base interface."""

from abc import ABC, abstractmethod
from multiprocessing import Queue as ProcessQueue
from multiprocessing.managers import SharedMemoryManager
from multiprocessing.shared_memory import ShareableList
from threading import Thread
from typing import Generic, TypeVar

from ..enums import Status
from ..exceptions import ChatApiStateException
from ..models import (
    ID,
    Error,
    Event,
    EventRequest,
    EventResponse,
    SessionEnd,
    StateError,
)
from ..state import State
from ..transports import Transport
from .handles import BaseInterfaceHandle

T = TypeVar("T", bound=BaseInterfaceHandle)


class BaseInterface(ABC, Generic[T]):
    """Base class for the interface between client and server."""

    def __init__(
        self,
        transport: Transport,
    ) -> None:
        self.state = State()
        self.transport = transport
        self.handles = dict[ID, T]()
        self.send_request_queue: "ProcessQueue[EventRequest | None]" = ProcessQueue()
        self.shared_memory_manager = SharedMemoryManager()
        self.shared_memory_manager.start()
        self.shared_status = self.shared_memory_manager.ShareableList(
            [Status.NOT_READY.value]
        )

        self.send_thread = Thread(target=self.run_send)
        self.receive_thread = Thread(target=self.run_receive)
        self.send_thread.start()
        self.receive_thread.start()

    @abstractmethod
    def new_handle(
        self,
        send_queue: "ProcessQueue[EventRequest | None]",
        shared_status: ShareableList[int],
    ) -> T:
        """Create a new handle for the interface."""
        raise NotImplementedError()

    def create_handle(self) -> T:
        """Create a process-safe handle for the interface."""
        handle = self.new_handle(
            send_queue=self.send_request_queue,
            shared_status=self.shared_status,
        )
        self.handles[handle.id] = handle
        return handle

    def run_send(self) -> None:
        """Run the send loop."""
        while True:
            event_request = self.send_request_queue.get()

            if event_request is None:
                break

            try:
                event = self.validate(event_request.event)
            except ChatApiStateException as e:
                self.handles[event_request.sender].response_queue.put(
                    EventResponse(
                        id=event_request.id,
                        result=StateError(message=str(e)),
                    )
                )
            except Exception as e:
                # TODO: handle other exceptions gracefully
                raise e
            else:
                self.handles[event_request.sender].response_queue.put(
                    EventResponse(
                        id=event_request.id,
                        result=event,
                    )
                )
                self.transport.send(event)

    def run_receive(self) -> None:
        """Run the receive loop."""
        while True:
            event = self.transport.receive()

            if event is None:
                event = SessionEnd()

            try:
                event = self.validate(event)
            except ChatApiStateException as e:
                self.transport.send(Error(message=str(e)))
            except Exception as e:
                # TODO: handle other exceptions gracefully
                raise e
            else:
                for handle in self.handles.values():
                    handle.receive_queue.put(event)
                if isinstance(event, SessionEnd):
                    self.close()
                    break

    def validate(self, event: Event) -> Event:
        """Validate the event."""
        event, status = self.state.validate(event)
        self.shared_status[0] = status.value
        return event

    def close(self) -> None:
        """Close the client."""
        self.transport.close()
        self.send_request_queue.put(None)
        self.shared_memory_manager.shutdown()

    def join(self) -> None:
        """Wait for the client to finish sending all queued actions/events."""
        self.transport.join()
        self.send_thread.join()
        self.receive_thread.join()
