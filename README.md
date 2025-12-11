# Chat API

## Development

### Install package in editable mode

```bash
uv pip install -e ".[websockets,fastapi,test]"
```

### Run tests (manually)

```bash
uv run tests/test_handles.py
```

## Installation
Base installation:
```bash
uv pip install "chat_api @ git+https://github.com/qatarai/chat_api.git"
```
Installing ready-to-use extensions for WebSockets and FastAPI (optional):
```bash
uv pip install "chat_api[websockets,fastapi] @ git+https://github.com/qatarai/chat_api.git"
```

## Flow
This diagram shows the flow of messages and states.

![Chat API state machine diagram](misc/sm.svg)


## Message specification

### Client → Server

- Config
  - event_type: EventType.CONFIG (int)
  - chat_id: uuid (string, optional)
  - input_mode: InputMode (int)
  - silence_duration: float (milliseconds; -1 enables on-device silence detection; only used for InputMode.Audio)
  - nchannels: int
  - sample_rate: int
  - sample_width: int
  - output_text: bool
  - output_audio: bool
  - output_video: bool

- Input (Audio)
  - bytes: audio (binary, streamed in arbitrary chunk sizes)

- InputText
  - event_type: EventType.INPUT_TEXT (int)
  - data: string

- Interrupt
  - event_type: EventType.INTERRUPT (int)
  - interrupt_type: InterruptType (int)

### Server → Client

- ServerReady
  - event_type: EventType.SERVER_READY (int)
  - chat_id: uuid (string)
  - request_id: uuid (string)

- OutputTranscription
  - event_type: EventType.OUTPUT_TRANSCRIPTION (int)
  - transcription: Transcription

- InputEnd (only when input_mode = Audio and silence is detected by server)
  - event_type: EventType.INPUT_END (int)

- OutputStage
  - event_type: EventType.OUTPUT_STAGE (int)
  - id: uuid (string)
  - parent_id: uuid (string)
  - title: string
  - description: string

- OutputTextContent
  - event_type: EventType.OUTPUT_TEXT_CONTENT (int)
  - id: uuid (string)
  - type: ContentType.TEXT (int)
  - stage_id: uuid (string)

- OutputFunctionCallContent
  - event_type: EventType.OUTPUT_FUNCTION_CALL_CONTENT (int)
  - id: uuid (string)
  - type: ContentType.FUNCTION_CALL (int)
  - stage_id: uuid (string)

- OutputAudioContent
  - event_type: EventType.OUTPUT_AUDIO_CONTENT (int)
  - id: uuid (string)
  - type: ContentType.AUDIO (int)
  - stage_id: uuid (string)
  - nchannels: int
  - sample_rate: int
  - sample_width: int

- OutputVideoContent
  - event_type: EventType.OUTPUT_VIDEO_CONTENT (int)
  - id: uuid (string)
  - type: ContentType.VIDEO (int)
  - stage_id: uuid (string)
  - fps: int
  - width: int
  - height: int

- OutputContentAddition
  - event_type: EventType.OUTPUT_CONTENT_ADDITION (int)
  - content_id: uuid (string)
  - …: additional metadata (implementation-defined)

- OutputMedia (streamed; multiple events allowed)
  - event_type: EventType.OUTPUT_MEDIA (int)
  - content_id: uuid (string; 16 bytes when binary-prefixed)
  - bytes: media (binary, streamed)

- OutputText (streamed; multiple events allowed)
  - event_type: EventType.OUTPUT_TEXT (int)
  - content_id: uuid (string)
  - data: string (chunk)

- OutputFunctionCall
  - event_type: EventType.OUTPUT_FUNCTION_CALL (int)
  - content_id: uuid (string)
  - data: string (JSON-encoded function call)

- OutputEnd
  - event_type: EventType.OUTPUT_END (int)

### Server <-> Client

- InputEnd (only when input_mode = Audio and silence is detected on device)
  - event_type: EventType.INPUT_END (int)

- SessionEnd
  - event_type: EventType.SESSION_END (int)

- Error
  - event_type: EventType.ERROR (int)
  - message: string

## Enums (all integer-valued)

- InputMode
  - 0: AUDIO
  - 1: TEXT

- ContentType
  - 0: AUDIO
  - 1: VIDEO
  - 2: TEXT
  - 3: FUNCTION_CALL

- EventType
  - 0: CONFIG
  - 1: INPUT_TEXT
  - 2: INPUT_MEDIA
  - 3: INPUT_END
  - 4: INTERRUPT
  - 5: SERVER_READY
  - 6: OUTPUT_TRANSCRIPTION
  - 7: OUTPUT_STAGE
  - 8: OUTPUT_TEXT_CONTENT
  - 9: OUTPUT_FUNCTION_CALL_CONTENT
  - 10: OUTPUT_AUDIO_CONTENT
  - 11: OUTPUT_VIDEO_CONTENT
  - 12: OUTPUT_CONTENT_ADDITION
  - 13: OUTPUT_TEXT
  - 14: OUTPUT_MEDIA
  - 15: OUTPUT_FUNCTION_CALL
  - 16: OUTPUT_END
  - 17: SESSION_END
  - 18: ERROR

- InterruptType
  - 0: USER
  - 1: SYSTEM

## Notes
- `uuid` refers to standard UUID string identifiers unless otherwise specified.
- The 16-byte `uuid` fields in media `Data` messages are UUID identifiers scoped to a content stream, used to correlate chunks.
- Audio/Video/Text data may be streamed in chunks; FunctionCall payloads are not chunked.
