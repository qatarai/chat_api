"""Dummy client to pair with `tests/test_dummy_server.py`.

Run the server first (it listens on ws://127.0.0.1:8086/ws by default),
then run this script to send a simple text input and print received outputs.
"""

import argparse
import asyncio
import wave

import numpy as np
from cv2 import IMREAD_COLOR, VideoWriter, VideoWriter_fourcc, imdecode
from websockets.asyncio.client import connect

from chat_api import Client, Event
from chat_api.enums import ContentType, EventType, InputMode
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
        audio_buffers: dict[str, bytearray] = {}
        video_buffers: dict[str, list[bytes]] = {}
        # Track content types to name files meaningfully
        contents: dict[str, OutputContent] = {}

        async def _on_output(c2s: Client, event: Event) -> None:
            if event.event_type not in [EventType.OUTPUT_MEDIA]:
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
                contents[str(event.id)] = event

            # Buffer media chunks by content
            if isinstance(event, OutputMedia):
                key = str(event.content_id)
                content = contents[key]
                if content.type == ContentType.AUDIO:
                    buf_audio = audio_buffers.setdefault(key, bytearray())
                    buf_audio.extend(event.data)
                elif content.type == ContentType.VIDEO:
                    buf_video = video_buffers.setdefault(key, [])
                    buf_video.append(event.data)

            # On OutputEnd, write all buffered media to files
            if isinstance(event, OutputEnd):
                for content_id_str, buf in audio_buffers.items():
                    content = contents[content_id_str]
                    filename = f"received_{content_id_str}.wav"
                    with wave.open(filename, "wb") as f:
                        f.setnchannels(content.nchannels)
                        f.setsampwidth(content.sample_width)
                        f.setframerate(content.sample_rate)
                        f.writeframes(buf)
                    print(f"Saved audio to {filename}")
                audio_buffers.clear()
                for content_id_str, buf in video_buffers.items():
                    content = contents[content_id_str]
                    filename = f"received_{content_id_str}.mp4"
                    video = VideoWriter(
                        filename,
                        VideoWriter_fourcc(*"mp4v"),
                        content.fps,
                        (content.width, content.height),
                    )
                    for frame in buf:
                        frame_np = np.frombuffer(frame, dtype=np.uint8)
                        frame_decoded = imdecode(frame_np, IMREAD_COLOR)
                        if frame_decoded is None:
                            continue
                        video.write(frame_decoded)
                    video.release()
                    print(f"Saved media to {filename}")
                video_buffers.clear()
                contents.clear()

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
