"""Process-safe handle for the interface."""

from abc import ABC
from multiprocessing import Queue as ProcessQueue
from multiprocessing.shared_memory import ShareableList
from threading import Event as ThreadEvent
from threading import Thread
from typing import Generic, TypeVar

from ...enums import InterruptType, Status
from ...exceptions import ChatApiException
from ...models import (
    ID,
    Event,
    EventRequest,
    EventResponse,
    InputEnd,
    Interrupt,
    SessionEnd,
    StateError,
    new_id,
)

T = TypeVar("T", bound=Event)


class Ack(Generic[T]):
    """Acknowledgment for an event request."""

    def __init__(self) -> None:
        self._signal = ThreadEvent()
        self._result: T | StateError | None = None

    def result(self) -> T | StateError:
        """Block until the result is available."""
        self._signal.wait()

        if self._result is None:
            raise ChatApiException("Result is not available. This should never happen.")

        return self._result

    def set_result(self, result: T | StateError) -> None:
        """Set the result of the acknowledgment."""
        self._result = result
        self._signal.set()


class BaseInterfaceHandle(ABC):
    """Base handle for the interface."""

    def __init__(
        self,
        send_queue: "ProcessQueue[EventRequest | None]",
        shared_status: ShareableList[int],
    ) -> None:
        self.id = new_id()
        self.send_queue = send_queue
        self.shared_status = shared_status
        self.receive_queue: "ProcessQueue[Event]" = ProcessQueue()
        self.response_queue: "ProcessQueue[EventResponse | None]" = ProcessQueue()
        self.acks = dict[ID, Ack]()

        self.chat_id: ID | None = None
        self.response_thread: Thread | None = None

    def start(self) -> None:
        """Start the handle."""
        self.response_thread = Thread(target=self.run_response)
        self.response_thread.start()

    def run_response(self) -> None:
        """Run the response loop."""
        while True:
            event_response = self.response_queue.get()

            if event_response is None:
                break

            self.acks[event_response.id].set_result(event_response.result)

    def close(self) -> None:
        """Close the handle."""
        self.response_queue.put(None)

    def join(self) -> None:
        """Join the handle."""
        if self.response_thread is not None:
            self.response_thread.join()
            self.response_thread = None

    @property
    def status(self) -> Status:
        """Get the status of the interface."""
        return Status(self.shared_status[0])

    def send(self, event: T) -> T | StateError:
        """Send an event to the interface."""
        event_request = EventRequest(id=new_id(), sender=self.id, event=event)
        self.acks[event_request.id] = Ack()
        self.send_queue.put(event_request)
        result = self.acks[event_request.id].result()
        return result

    def receive(self) -> Event:
        """Receive an event from the interface."""
        return self.receive_queue.get()

    @staticmethod
    def new_uuid() -> ID:
        """Generate a random ID."""
        return new_id()

    def end_input(self) -> InputEnd | StateError:
        """End the input."""
        event = InputEnd()
        return self.send(event)

    def interrupt(
        self,
        interrupt_type: InterruptType,
    ) -> Interrupt | StateError:
        """Interrupt the request."""
        event = Interrupt(interrupt_type=interrupt_type)
        return self.send(event)

    def end_session(self) -> SessionEnd | StateError:
        """End the session."""
        event = SessionEnd()
        return self.send(event)
