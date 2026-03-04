"""In-memory transport useful for tests/examples."""

from .base import ThreadQueue, Transport


class InMemoryTransport(Transport):
    """In-memory transport useful for tests/examples."""

    def __init__(self) -> None:
        self.dummy_data_queue: ThreadQueue[str | bytes | None] = ThreadQueue()
        super().__init__()

    def send_impl(self, data: str | bytes) -> None:
        pass

    def receive_impl(self) -> str | bytes | None:
        data = self.dummy_data_queue.get()
        self.dummy_data_queue.task_done()
        return data

    def dummy_data(self, data: str | bytes) -> None:
        """Put dummy data into the queue."""
        self.dummy_data_queue.put(data)

    def close(self) -> None:
        self.dummy_data_queue.put(None)
        super().close()
