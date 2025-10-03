"""Dummy server to pair with `tests/test_dummy_client.py`.

Run this script, then run the client script to test the chat API.
"""

from pathlib import Path
from typing import Optional

import fastapi
import uvicorn

from chat_api.clients.server import Server
from chat_api.enums import ContentType, InputMode
from chat_api.models import (
    Config,
    Event,
    InputEnd,
    InputMedia,
    InputText,
    Segment,
    Transcription,
)
from chat_api.transports.starlette import StarletteTransport

app = fastapi.FastAPI(debug=True)


@app.websocket("/ws")
async def websocket_endpoint(websocket: fastapi.WebSocket) -> None:
    """WebSocket endpoint for testing the chat API."""
    await websocket.accept()
    tx = StarletteTransport(websocket)

    input_mode: Optional[InputMode] = None
    input_ended: bool = False
    last_transcription_end: int = 1

    def on_input(s2c: Server, evt: Event) -> None:
        nonlocal input_mode, input_ended, last_transcription_end
        print(f"Received event: {evt}")

        if isinstance(evt, Config):
            input_mode = evt.input_mode

        elif isinstance(evt, (InputText, InputMedia)):
            if input_mode == InputMode.AUDIO and not input_ended:
                transcription = Transcription(
                    segments=[
                        Segment(
                            text="listening...",
                            start=end - 1.0,
                            end=end,
                        )
                        for end in range(0, last_transcription_end, 1)
                    ],
                )
                s2c.transcription(transcription)
                last_transcription_end += 1

        elif isinstance(evt, InputEnd):
            input_ended = True

            # Stage 1: text outputs
            stage1, _ = s2c.stage(title="Stage 1", description="Text outputs")
            for i in range(2):
                stream, _ = s2c.text_stream(stage_id=stage1.id)
                stream.send("Hello")
                stream.send(f", world! {i}\n")
                stream.end()
            for i in range(2):
                stream, _ = s2c.text_stream(stage_id=stage1.id)
                stream.send("Content 2")
                stream.send(f" part {i}\n")
                stream.end()

            # Stage 2: media outputs
            stage2, _ = s2c.stage(title="Stage 2", description="Media outputs")
            image_path = Path(__file__).parent / "three.png"
            stream2, _ = s2c.media_stream(
                content_type=ContentType.AUDIO,
                stage_id=stage2.id,
            )
            chunk_size = 1024
            with image_path.open("rb") as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    stream2.send(chunk)
            stream2.end()

            # End of output
            s2c.end()

    s2c = Server(tx, event_callback=on_input)
    await s2c.join()


# run the app
if __name__ == "__main__":
    uvicorn.run(
        "test_dummy_server:app",
        host="0.0.0.0",
        port=8086,
        reload=True,
    )
