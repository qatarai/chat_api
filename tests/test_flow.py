"""Testing."""

import argparse
import asyncio
from enum import Enum

from websockets.asyncio.client import connect
from websockets.asyncio.server import serve

from chat_api import Client, Config, Event, OutputEnd, Server
from chat_api.models import InputEnd, ServerReady
from chat_api.transports import InMemoryTransport, Transport
from chat_api.transports.websockets import WebsocketsTransport


class TransportType(Enum):
    """Transport type."""

    INMEMORY = "inmemory"
    WEBSOCKETS = "websockets"

    async def setup_transports(self) -> tuple[Transport, Transport]:
        """Setup the transports."""
        if self == TransportType.INMEMORY:
            return setup_inmemory_transports()
        elif self == TransportType.WEBSOCKETS:
            return await setup_websockets_transports()
        else:
            raise ValueError(f"Invalid transport type: {self}")


def setup_inmemory_transports() -> tuple[InMemoryTransport, InMemoryTransport]:
    """Create and cross-wire a pair of in-memory transports.

    Returns a tuple of (server_to_client_transport, client_to_server_transport).
    """
    s2c_tx = InMemoryTransport()
    c2s_tx = InMemoryTransport()
    s2c_tx.on_event_sent(c2s_tx.notify_event_received_listeners)
    c2s_tx.on_event_sent(s2c_tx.notify_event_received_listeners)
    return s2c_tx, c2s_tx


async def setup_websockets_transports():
    """Initialize websockets server+client and create transports for each side.

    Returns a tuple of (server_to_client_transport, client_to_server_transport).
    """
    server_conn_q = asyncio.Queue()

    async def handler(ws):
        await server_conn_q.put(ws)
        await asyncio.Future()  # keep the server connection open

    server = await serve(handler, "127.0.0.1", 0)
    host, port = server.sockets[0].getsockname()[:2]
    client_conn = await connect(f"ws://{host}:{port}")
    server_conn = await server_conn_q.get()

    s2c_tx = WebsocketsTransport(server_conn)
    c2s_tx = WebsocketsTransport(client_conn)
    return s2c_tx, c2s_tx


def print_event(server: bool, event: Event) -> None:
    """Print the event."""
    print(
        f"----- {'Client -> Server' if server else 'Server -> Client'} -----"
    )
    print(event)


async def test_complete_flow(transport_type: TransportType):
    """Test the complete flow."""

    # Prepare interactions
    def on_input(s2c: Server, event: Event) -> None:
        print_event(server=True, event=event)

        if isinstance(event, Config):
            s2c.ready(event)

        if isinstance(event, InputEnd):
            stage, _ = s2c.stage(
                title="stage 1",
                description="stage 1",
            )
            content, _ = s2c.text_content(
                stage_id=stage.id,
            )

            stream, _ = s2c.text_stream(
                stage_id=stage.id,
                content_id=content.id,
            )
            stream.send("hello")
            stream.send("world")
            stream.end()
            s2c.end_output()

    max_requests = 1
    n_requests = 0

    def on_output(c2s: Client, event: Event) -> None:
        nonlocal n_requests
        print_event(server=False, event=event)

        if isinstance(event, ServerReady):
            c2s.text("hello")
            c2s.end_input()
            n_requests += 1

        elif isinstance(event, OutputEnd):
            if n_requests >= max_requests:
                c2s.end_session()

            else:
                c2s.text("hello")
                c2s.end_input()
                n_requests += 1

    # Initialize the server and client transports
    s2c_tx, c2s_tx = await transport_type.setup_transports()

    s2c = Server(
        s2c_tx,
        event_callback=on_input,
    )

    c2s = Client(
        c2s_tx,
        event_callback=on_output,
    )

    await asyncio.gather(
        s2c.join(),
        c2s.join(),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--transport-type",
        type=TransportType,
        default=TransportType.INMEMORY,
    )
    args = parser.parse_args()

    asyncio.run(test_complete_flow(args.transport_type))
