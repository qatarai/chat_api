"""Simple test for server and client handles using FastAPI and WebSockets."""

import argparse
import asyncio
import logging
import time
import wave
from threading import Thread

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from websockets.sync.client import connect

from chat_api import Event, InputEnd
from chat_api.enums import InputMode
from chat_api.interface import ClientInterface, ServerInterface
from chat_api.models import (
    Config,
    Error,
    InputText,
    OutputAudioContent,
    OutputEnd,
    OutputMedia,
    OutputStage,
    OutputText,
    OutputTextContent,
    ServerReady,
    StateError,
)
from chat_api.transports.starlette import StarletteTransport
from chat_api.transports.websockets import WebsocketsTransport

# Create FastAPI app with WebSocket endpoint
app = FastAPI()


def handle_result(result: Event | StateError) -> Event | StateError:
    """Call a function and return the result."""
    if isinstance(result, StateError):
        print(f"Server error: {result}")
    return result


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint that uses ServerInterface."""
    await websocket.accept()
    transport = StarletteTransport(websocket)
    server_interface = ServerInterface(transport)
    server_handle = server_interface.create_handle()

    def server_loop():
        """Server loop that handles events."""
        text = ""

        # try:
        while True:
            event = server_handle.receive()
            if isinstance(event, Config):
                # Respond with ServerReady
                request_id = server_handle.new_uuid()
                handle_result(server_handle.ready(request_id=request_id))

            elif isinstance(event, InputText):
                text = event.data

            elif isinstance(event, InputEnd):
                # Echo the text back
                stage_id = server_handle.new_uuid()
                handle_result(
                    server_handle.stage(
                        title="Echo Stage",
                        description="Echoing your message",
                        stage_id=stage_id,
                    )
                )
                content_id = server_handle.new_uuid()
                handle_result(
                    server_handle.text_content(stage_id=stage_id, content_id=content_id)
                )
                handle_result(
                    server_handle.text(content_id=content_id, data=f"Echo: {text}")
                )

                # Send audio
                stage_id_audio = server_handle.new_uuid()
                handle_result(
                    server_handle.stage(
                        title="Audio Stage",
                        description="Sending mario audio",
                        stage_id=stage_id_audio,
                    )
                )

                with wave.open("tests/mario.wav", "rb") as wf:
                    nchannels = wf.getnchannels()
                    sample_rate = wf.getframerate()
                    sample_width = wf.getsampwidth()
                    audio_data = wf.readframes(wf.getnframes())

                content_id_audio = server_handle.new_uuid()
                handle_result(
                    server_handle.audio_content(
                        stage_id=stage_id_audio,
                        content_id=content_id_audio,
                        nchannels=nchannels,
                        sample_rate=sample_rate,
                        sample_width=sample_width,
                    )
                )

                chunk_size = sample_rate * sample_width * nchannels
                while len(audio_data) > 0:
                    handle_result(
                        server_handle.audio(
                            content_id=content_id_audio,
                            data=audio_data[: min(chunk_size, len(audio_data))],
                        )
                    )
                    audio_data = audio_data[min(chunk_size, len(audio_data)) :]

                handle_result(server_handle.end_output())

        # except Exception as e:
        #     print(f"Server error: {e}")
        # finally:
        #     server_handle.close()
        #     server_interface.close()
        #     server_handle.join()
        #     server_interface.join()

    server_thread = Thread(target=server_loop, daemon=True)
    server_thread.start()

    try:
        while server_thread.is_alive():
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        pass
    finally:
        server_thread.join(timeout=2.0)


def run_server():
    """Run the FastAPI server."""
    uvicorn.run(app, host="localhost", port=9000, log_level="error")


def test_basic_communication():
    """Test basic communication: Config -> ServerReady -> Text -> Output."""
    print("Starting server...")
    server_thread = Thread(target=run_server, daemon=True)
    server_thread.start()
    time.sleep(1.5)  # Wait for server to start

    try:
        print("Connecting client...")
        connection = connect("ws://localhost:9000/ws")
        transport = WebsocketsTransport(connection, is_client=True)
        client_interface = ClientInterface(transport)  # type: ignore[abstract]
        client_handle = client_interface.create_handle()

        # Send Config
        print("Sending Config...")
        config = Config(input_mode=InputMode.TEXT, output_text=True, output_audio=True)
        handle_result(client_handle.send(config))

        # Receive ServerReady
        print("Receiving ServerReady...")
        event = client_handle.receive()
        if not isinstance(event, ServerReady):
            print(f"ERROR: Expected ServerReady, got {type(event)}")
            return False
        print(
            f"✓ Received ServerReady: chat_id={event.chat_id}, request_id={event.request_id}"
        )

        # Send text input
        print("Sending text input...")
        test_message = "Hello, server!"
        handle_result(client_handle.text(test_message))
        handle_result(client_handle.end_input())

        # Receive output events
        print("Receiving output events...")
        events = []
        received_audio_data = b""

        while True:
            event = client_handle.receive()
            if isinstance(event, Error):
                print(f"ERROR: {event.message}")
                return False
            elif isinstance(event, OutputEnd):
                events.append(event)
                break
            elif isinstance(event, OutputMedia):
                received_audio_data += event.data
            else:
                events.append(event)

        # Verify events
        if not isinstance(events[0], OutputStage):
            print(f"ERROR: Expected OutputStage, got {type(events[0])}")
            return False
        if not isinstance(events[1], OutputTextContent):
            print(f"ERROR: Expected OutputTextContent, got {type(events[1])}")
            return False
        if not isinstance(events[2], OutputText):
            print(f"ERROR: Expected OutputText, got {type(events[2])}")
            return False
        if not isinstance(events[3], OutputStage):
            print(f"ERROR: Expected OutputStage, got {type(events[3])}")
            return False
        if not isinstance(events[4], OutputAudioContent):
            print(f"ERROR: Expected OutputAudioContent, got {type(events[3])}")
            return False
        if not isinstance(events[5], OutputEnd):
            print(f"ERROR: Expected OutputEnd, got {type(events[4])}")
            return False

        # Verify echo content
        output_text = events[2]
        if test_message not in output_text.data:
            print(
                f"ERROR: Expected '{test_message}' in output, got '{output_text.data}'"
            )
            return False

        print(f"✓ Received output: {output_text.data}")

        if len(received_audio_data) == 0:
            print("ERROR: No audio data received")
            return False

        # Save received audio
        try:
            with wave.open("received_mario.wav", "wb") as wf:
                wf.setnchannels(events[4].nchannels)
                wf.setframerate(events[4].sample_rate)
                wf.setsampwidth(events[4].sample_width)
                wf.writeframes(received_audio_data)
            print("✓ Saved received_mario.wav")
        except Exception as e:
            print(f"ERROR: Failed to save received audio: {e}")
            return False

        # End the session
        handle_result(client_handle.end_session())

        # Cleanup
        client_handle.close()
        client_interface.close()
        client_handle.join()
        client_interface.join()

        print("✓ All tests passed!")
        return True

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test handles")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)

    success = test_basic_communication()
    exit(0 if success else 1)
