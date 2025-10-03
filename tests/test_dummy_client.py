"""Dummy client to pair with `tests/test_dummy_server.py`.

Run the server first (it listens on ws://127.0.0.1:8086/ws by default),
then run this script to send a simple text input and print received outputs.
"""

import argparse
import asyncio

from websockets.asyncio.client import connect

from chat_api import Client, Event
from chat_api.enums import ContentType, InputMode
from chat_api.models import (
    Config,
    OutputContent,
    OutputEnd,
    OutputMedia,
    ServerReady,
)
from chat_api.transports.websockets import WebsocketsTransport


# Text input
async def run_client1(ws_url: str) -> None:
    """Connect to the server and drive a basic interaction."""

    async with connect(ws_url) as websocket:
        tx = WebsocketsTransport(websocket)

        def on_output(c2s: Client, event: Event) -> None:
            print(f"Received event: {event}")

            if isinstance(event, ServerReady):
                c2s.text("Hello from dummy client!")
                c2s.end_input()

        c2s = Client(
            tx,
            event_callback=on_output,
        )

        await c2s.join()


# Media input
async def run_client2(ws_url: str) -> None:
    """Connect to the server and drive a basic interaction."""

    async with connect(ws_url) as websocket:
        tx = WebsocketsTransport(websocket)
        # Buffers for received media keyed by content_id (as string)
        media_buffers: dict[str, bytearray] = {}
        # Track content types to name files meaningfully
        content_types: dict[str, ContentType] = {}

        async def _on_output(c2s: Client, event: Event) -> None:
            print(f"Received event: {event}")

            if isinstance(event, ServerReady):
                stream = c2s.media_stream()
                for i in range(3):
                    stream.send(
                        bytes(f"Hello from dummy client part {i}!\n", "utf-8")
                    )
                    await asyncio.sleep(1)
                stream.end()

            # Track content metadata
            if isinstance(event, OutputContent):
                content_types[str(event.id)] = event.type

            # Buffer media chunks by content
            if isinstance(event, OutputMedia):
                key = str(event.content_id)
                buf = media_buffers.setdefault(key, bytearray())
                buf.extend(event.data)

            # On OutputEnd, write all buffered media to files
            if isinstance(event, OutputEnd):
                for content_id_str, buf in media_buffers.items():
                    ctype = content_types.get(content_id_str)
                    # Use content type name in filename if available
                    type_name = (
                        "audio"
                        if ctype == ContentType.AUDIO
                        else (
                            "video"
                            if ctype == ContentType.VIDEO
                            else (
                                "text"
                                if ctype == ContentType.TEXT
                                else (
                                    "function"
                                    if ctype == ContentType.FUNCTION_CALL
                                    else "media"
                                )
                            )
                        )
                    )
                    filename = f"received_{type_name}_{content_id_str}.bin"
                    with open(filename, "wb") as f:
                        f.write(buf)
                    print(f"Saved media to {filename}")

                media_buffers.clear()
                content_types.clear()

        def on_output(c2s: Client, event: Event) -> None:
            asyncio.create_task(_on_output(c2s, event))

        c2s = Client(
            tx,
            event_callback=on_output,
            config=Config(
                input_mode=InputMode.AUDIO,
            ),
        )

        await c2s.join()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--ws-url",
        default="ws://127.0.0.1:8086/ws",
        help="WebSocket URL of the dummy server",
    )
    args = parser.parse_args()

    asyncio.run(run_client2(args.ws_url))
