"""Testing."""

from chat_api import (
    ClientToServer,
    Event,
    InputText,
    OutputInitialization,
    ServerToClient,
)
from chat_api.enums import ContentType
from chat_api.transport import InMemoryTransport


def print_event(server: bool, event: Event) -> None:
    """Print the event."""
    print(
        f"----- {'Client -> Server' if server else 'Server -> Client'} -----"
    )
    print(event)


def test_complete_flow():
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

    # Initialize the server and client
    s2c_tx = InMemoryTransport()
    c2s_tx = InMemoryTransport()
    s2c_tx.on_event_sent(c2s_tx.event_received)
    c2s_tx.on_event_sent(s2c_tx.event_received)

    s2c = ServerToClient(
        s2c_tx,
        on_input=on_input,
    )

    c2s = ClientToServer(
        c2s_tx,
        on_output=on_output,
    )

    s2c.end()

    del s2c, c2s
    print("done")


test_complete_flow()
