# Chat API

## Development

### Create venv (Python 3.10+)

Run these from the project root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install --upgrade setuptools
pip install -r requirements.txt
```

### Install package in editable mode

```bash
pip install -e .
```

### Run tests (manually)

```bash
python tests/test_basic.py
```

## Usage

Generally, the steps are:
1. Implement the `Transport` interface for your specific use case (e.g., websocket, HTTP, etc.).
2. Create a `ServerToClient` or `ClientToServer` instance, passing in your transport.
3. Start sending/receiving events.

Refer to `tests/test_basic.py` for the following basic demo on the complete client-server flow:
![Basic demo](./misc/basic_flow.png)

## Sequence diagram

```mermaid
sequenceDiagram
    autonumber

    participant C as Client
    participant S as Server

    Note over C,S: Audio/Video bytes stream in chunks.
    Note over C,S: Text may stream via repeated OutputText events.
    Note over C,S: FunctionCall does not stream.
    Note over C,S: Legend<br/>blue = Client to Server<br/>green = Server to Client

    rect rgba(51,136,255,0.18)
        Note over C,S: Config Event<br/>- event_type: EventType.Config<br/>- chat_id: uuid?<br/>- input_mode: InputMode<br/>- output_text: bool<br/>- output_audio: bool<br/>- output_video: bool<br/>- silence_duration: float (ms, -1 => device)
        C->>S: Config
    end

    alt input_mode = Audio
        loop Input audio chunks
            rect rgba(51,136,255,0.18)
                Note over C,S: Input (Audio)<br/>- bytes: audio
                C-->>S: Audio Chunk
            end
        end
        rect rgba(51,136,255,0.18)
            Note over C,S: InputEnd<br/>Condition: input_mode = Audio AND silence_duration = -1<br/>- event_type: EventType.InputEnd
            C->>S: InputEnd
        end
    else input_mode = Text
        rect rgba(51,136,255,0.18)
            Note over C,S: InputText<br/>- event_type: EventType.InputText<br/>- data: string
            C->>S: InputText
        end
    end

    rect rgba(51,136,255,0.18)
        Note over C,S: InputInterrupt<br/>Condition: can occur at any time<br/>- event_type: EventType.InputInterrupt<br/>- interrupt_type: InterruptType
        C->>S: InputInterrupt
    end

    rect rgba(76,175,80,0.18)
        Note over C,S: OutputInitialization<br/>- event_type: EventType.OutputInitialization<br/>- chat_id: uuid<br/>- request_id: uuid
        S-->>C: OutputInitialization
    end

    rect rgba(76,175,80,0.18)
        Note over C,S: InputEnd (echo)<br/>Condition: input_mode = Audio AND silence_duration = -1<br/>- event_type: EventType.InputEnd
        S-->>C: InputEnd (echo)
    end

    loop For each stage
        rect rgba(76,175,80,0.18)
            Note over C,S: OutputStage<br/>- event_type: EventType.OutputStage<br/>- id: uuid<br/>- parent_id: uuid<br/>- title: string<br/>- description: string
            S-->>C: OutputStage
        end

        rect rgba(76,175,80,0.18)
            Note over C,S: OutputContent<br/>- event_type: EventType.OutputContent<br/>- id: uuid<br/>- type: ContentType<br/>- stage_id: uuid
            S-->>C: OutputContent
        end

        rect rgba(76,175,80,0.18)
            Note over C,S: OutputContentAddition<br/>- event_type: EventType.OutputContentAddition<br/>- content_id: uuid<br/>- …
            S-->>C: OutputContentAddition
        end

        alt type = ContentType.Audio
            loop Audio data chunks
                rect rgba(76,175,80,0.18)
                    Note over C,S: Data (Audio)<br/>Info: each chunk prefixed with uuid (16 bytes)<br/>- uuid: uuid (16 bytes)<br/>- bytes: audio
                    S-->>C: Audio Chunk
                end
            end
        else type = ContentType.Video
            loop Video data chunks
                rect rgba(76,175,80,0.18)
                    Note over C,S: Data (Video)<br/>Info: each chunk prefixed with uuid (16 bytes)<br/>- uuid: uuid (16 bytes)<br/>- bytes: video
                    S-->>C: Video Chunk
                end
            end
        else type = ContentType.Text
            loop Text data chunks
                rect rgba(76,175,80,0.18)
                    Note over C,S: OutputText<br/>- event_type: EventType.OutputText<br/>- data: string (chunk)
                    S-->>C: Text Chunk
                end
            end
        else type = ContentType.FunctionCall
            rect rgba(76,175,80,0.18)
                Note over C,S: OutputFunctionCall<br/>- event_type: EventType.OutputFunctionCall<br/>- data: string (json)
                S-->>C: FunctionCall
            end
        end
    end

    rect rgba(76,175,80,0.18)
        Note over C,S: OutputEnd<br/>- event_type: EventType.OutputEnd
        S-->>C: OutputEnd
    end
```

## Message specification

### Client → Server

- Config
  - event_type: EventType.Config (int)
  - chat_id: uuid (string, optional)
  - input_mode: InputMode (int)
  - output_text: bool
  - output_audio: bool
  - output_video: bool
  - silence_duration: float (milliseconds; -1 enables on-device silence detection; only used for InputMode.Audio)

- Input (Audio)
  - bytes: audio (binary, streamed in arbitrary chunk sizes)

- InputText
  - event_type: EventType.InputText (int)
  - data: string

- InputEnd (only when input_mode = Audio and silence is detected on device)
  - event_type: EventType.InputEnd (int)

- InputInterrupt
  - event_type: EventType.InputInterrupt (int)
  - interrupt_type: InterruptType (int)

### Server → Client

- OutputInitialization
  - event_type: EventType.OutputInitialization (int)
  - chat_id: uuid (string)
  - request_id: uuid (string)

- InputEnd (only when input_mode = Audio and silence is detected by server)
  - event_type: EventType.InputEnd (int)

- OutputStage
  - event_type: EventType.OutputStage (int)
  - id: uuid (string)
  - parent_id: uuid (string)
  - title: string
  - description: string

- OutputContent
  - event_type: EventType.OutputContent (int)
  - id: uuid (string)
  - type: ContentType (int)
  - stage_id: uuid (string)

- OutputContentAddition
  - event_type: EventType.OutputContentAddition (int)
  - content_id: uuid (string)
  - …: additional metadata (implementation-defined)

- Data (Audio)
  - uuid: uuid (16 bytes; per-content stream chunk identifier)
  - bytes: audio (binary, streamed)

- Data (Video)
  - uuid: uuid (16 bytes; per-content stream chunk identifier)
  - bytes: video (binary, streamed)

- OutputText (streamed; multiple events allowed)
  - event_type: EventType.OutputText (int)
  - data: string (chunk)

- OutputFunctionCall
  - event_type: EventType.OutputFunctionCall (int)
  - data: string (JSON-encoded function call)

- OutputEnd
  - event_type: EventType.OutputEnd (int)

## Enums (all integer-valued)

- InputMode
  - 0: Audio
  - 1: Text

- ContentType
  - 0: Audio
  - 1: Video
  - 2: Text
  - 3: FunctionCall

- EventType
  - 0: Config
  - 1: InputText
  - 2: InputMedia
  - 3: InputEnd
  - 4: InputInterrupt
  - 5: OutputInitialization
  - 6: OutputStage
  - 7: OutputContent
  - 8: OutputContentAddition
  - 9: OutputText
  - 10: OutputMedia
  - 11: OutputFunctionCall
  - 12: OutputEnd

- InterruptType
  - 0: User
  - 1: System

## Notes
- `uuid` refers to standard UUID string identifiers unless otherwise specified.
- The 16-byte `uuid` fields in media `Data` messages are UUID identifiers scoped to a content stream, used to correlate chunks.
- Audio/Video/Text data may be streamed in chunks; FunctionCall payloads are not chunked.
