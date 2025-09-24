"""Testing."""

import argparse
import asyncio
from enum import Enum

from websockets.asyncio.client import connect
from websockets.asyncio.server import serve

from chat_api import (
    ClientToServer,
    Event,
    InputText,
    OutputInitialization,
    ServerToClient,
)
from chat_api.enums import ContentType
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
    s2c_tx.on_event_sent(c2s_tx.event_received)
    c2s_tx.on_event_sent(s2c_tx.event_received)
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
    def on_input(s2c: ServerToClient, event: Event) -> None:
        print_event(server=True, event=event)

        if isinstance(event, InputText):
            stage = s2c.stage(
                title="stage 1",
                description="stage 1",
            )
            content = s2c.content(
                content_type=ContentType.TEXT,
                stage_id=stage.id,
            )

            stream = s2c.text_stream(
                stage_id=stage.id,
                content_id=content.id,
            )
            stream.send("hello")
            stream.send("world")
            stream.end()

    def on_output(c2s: ClientToServer, event: Event) -> None:
        print_event(server=False, event=event)

        if isinstance(event, OutputInitialization):
            c2s.text("hello")

    # Initialize the server and client transports
    s2c_tx, c2s_tx = await transport_type.setup_transports()

    s2c = ServerToClient(
        s2c_tx,
        on_input=on_input,
    )

    c2s = ClientToServer(
        c2s_tx,
        on_output=on_output,
    )

    await asyncio.sleep(1)
    s2c.end()

    del s2c, c2s
    print("done")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--transport-type",
        type=TransportType,
        default=TransportType.INMEMORY,
    )
    args = parser.parse_args()

    asyncio.run(test_complete_flow(args.transport_type))
