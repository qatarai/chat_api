"""Test transports."""

import argparse
import asyncio
import logging
import sys
import time
from threading import Thread

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from websockets import ConnectionClosed
from websockets.sync.client import connect
from websockets.sync.connection import Connection
from websockets.sync.server import serve

from chat_api.models import InputText
from chat_api.transports import InMemoryTransport, Transport
from chat_api.transports.starlette import StarletteTransport
from chat_api.transports.websockets import WebsocketsTransport


def recv(t: Transport) -> None:
    """Receive events from the transport."""
    while True:
        event = t.receive()
        if event is None:
            break
        print(f"Received event: {event}")


def test_in_memory_transport() -> None:
    """Test in-memory transport."""
    transport = InMemoryTransport()
    server_thread = Thread(target=recv, args=(transport,))
    server_thread.start()

    # Send
    transport.send(InputText(data="Hello, world! I am sending."))
    transport.wait_for_send()

    # Receive
    transport.dummy_data(
        InputText(data="Hello, world! I am receiving.").model_dump_json()
    )

    # Close
    transport.close()
    transport.join()
    server_thread.join()


def echo(websocket: Connection):
    """Echo server."""
    try:
        while True:
            message = websocket.recv()
            websocket.send(message)
    except ConnectionClosed:
        pass


def test_websocket_transport() -> None:
    """Test websocket transport using a localhost echo server."""

    shutdown = None

    def run_echo_server():
        nonlocal shutdown
        with serve(echo, "localhost", 8765) as server:
            shutdown = server.shutdown
            server.serve_forever()

    server_thread = Thread(target=run_echo_server, daemon=True)
    server_thread.start()

    connection = connect("ws://localhost:8765")
    transport = WebsocketsTransport(connection)
    server_thread_recv = Thread(target=recv, args=(transport,))
    server_thread_recv.start()

    transport.send(InputText(data="Hello, world! I am sending via websocket."))
    transport.wait_for_send()

    transport.close()
    transport.join()
    server_thread_recv.join()


def test_starlette_transport() -> None:
    """
    Test StarletteTransport using FastAPI's websocket support.
    This spins up a FastAPI websocket server that uses StarletteTransport
    with a real Starlette WebSocket, and a simple websocket client.
    """
    app = FastAPI()

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        await websocket.accept()
        transport = StarletteTransport(websocket)

        def echo_loop():
            try:
                while True:
                    event = transport.receive()
                    if event is None:
                        break
                    transport.send(event)
            except (WebSocketDisconnect, ConnectionClosed):
                pass
            finally:
                transport.close()
                transport.join()

        echo_thread = Thread(target=echo_loop, daemon=True)
        echo_thread.start()

        try:
            while echo_thread.is_alive():
                await asyncio.sleep(0.1)
        except WebSocketDisconnect:
            pass
        finally:
            echo_thread.join(timeout=1.0)

    def run_uvicorn():
        uvicorn.run(app, host="localhost", port=8765)

    server_thread = Thread(target=run_uvicorn, daemon=True)
    server_thread.start()

    # Wait for uvicorn to start
    time.sleep(1)

    connection = connect("ws://localhost:8765/ws")
    transport = WebsocketsTransport(connection)
    server_thread_recv = Thread(target=recv, args=(transport,))
    server_thread_recv.start()

    transport.send(InputText(data="Hello, world! I am sending via Starlette/FastAPI."))
    transport.wait_for_send()

    # Wait for echo'ed event to be received
    time.sleep(1)

    transport.close()
    transport.join()
    server_thread_recv.join()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test different transports")
    parser.add_argument(
        "--transport",
        choices=["inmemory", "websocket", "starlette"],
        default="inmemory",
        help="Transport to test (inmemory, websocket, or starlette)",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)

    if args.transport == "inmemory":
        test_in_memory_transport()
    elif args.transport == "websocket":
        test_websocket_transport()
    elif args.transport == "starlette":
        test_starlette_transport()
    else:
        print(f"Unknown transport type: {args.transport}", file=sys.stderr)
        sys.exit(1)
