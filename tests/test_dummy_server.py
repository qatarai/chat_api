"""Dummy server to pair with `tests/test_dummy_client.py`.

Run this script, then run the client script to test the chat API.
"""

import wave
from pathlib import Path
from typing import Optional

import fastapi
import uvicorn
from cv2 import (
    CAP_PROP_FPS,
    CAP_PROP_FRAME_HEIGHT,
    CAP_PROP_FRAME_WIDTH,
    VideoCapture,
    imencode,
)

from chat_api.clients.server import Server
from chat_api.enums import InputMode
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

            # Stage 1: Text outputs
            stage1, _ = s2c.stage(title="Stage 1", description="Text outputs")
            stream, _ = s2c.text_stream(stage_id=stage1.id)
            stream.send("Hello")
            stream.send(", world!")
            stream.end()
            stream, _ = s2c.text_stream(stage_id=stage1.id)
            stream.send("This is a fixed text stream.")
            stream.send(" The input is not considered")
            stream.end()

            # Stage 2: Audio outputs
            stage2, _ = s2c.stage(title="Stage 2", description="Audio outputs")
            image_path = Path(__file__).parent / "mario.wav"
            with wave.open(str(image_path), "rb") as reader:
                nchannels = reader.getnchannels()
                sample_rate = reader.getframerate()
                sample_width = reader.getsampwidth()
                stream1, _ = s2c.text_stream(stage_id=stage2.id)
                stream1.send(f"The stream's sample rate is {sample_rate} Hz.")
                stream1.send(
                    f" The sample format is pcm{sample_width * 8}bits."
                )
                stream1.end()
                stream2, _ = s2c.audio_stream(
                    nchannels=nchannels,
                    sample_rate=sample_rate,
                    sample_width=sample_width,
                    stage_id=stage2.id,
                )
                while frames := reader.readframes(16000):
                    stream2.send(frames)
                stream2.end()

            # Stage 3: Video outputs
            stage3, _ = s2c.stage(title="Stage 3", description="Video outputs")
            video_path = Path(__file__).parent / "marcello.mp4"
            video = VideoCapture(str(video_path))
            stream3, _ = s2c.video_stream(
                fps=int(video.get(CAP_PROP_FPS)),
                width=int(video.get(CAP_PROP_FRAME_WIDTH)),
                height=int(video.get(CAP_PROP_FRAME_HEIGHT)),
                stage_id=stage3.id,
            )
            while True:
                ret, frame = video.read()
                if not ret:
                    break
                ret, frame_encoded = imencode(".jpg", frame)
                if not ret:
                    break
                stream3.send(frame_encoded.tobytes())
            stream3.end()
            video.release()

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
