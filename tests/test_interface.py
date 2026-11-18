import socket
import threading
import unittest

from interface.client_state import (
    ClientPhase,
    ClientPresentationState,
    ClientStateError,
)
from server.server import GameServer
from shared.protocol import encode_message, make_message
from shared.telemetry import TraceEvent
from shared.transport import MessageChannel, connect_to_server


class ClientPresentationStateTests(unittest.TestCase):
    def identified_state(self) -> ClientPresentationState:
        state = ClientPresentationState()
        state.begin_connection()
        state.connection_established()
        state.apply_server_message(make_message("WELCOME", client_id="c1"))
        return state

    def start_match(self, state: ClientPresentationState) -> None:
        state.apply_server_message(make_message("WAITING"))
        state.apply_server_message(
            make_message("START", game_id="g1", mark="X", first_turn="X")
        )
        state.apply_server_message(
            make_message(
                "BOARD",
                game_id="g1",
                board=[["", "", ""] for _ in range(3)],
                turn="X",
                revision=0,
            )
        )

    def test_full_presentation_flow_waits_for_official_board(self) -> None:
        state = self.identified_state()
        self.start_match(state)
        state.mark_move_sent(0, 0)
        state.apply_server_message(
            make_message(
                "MOVE_RESULT",
                game_id="g1",
                status="ACCEPTED",
                row=0,
                col=0,
                revision=1,
            )
        )
        self.assertEqual(state.board[0][0], "")
        self.assertEqual(state.expected_revision, 1)

        state.apply_server_message(
            make_message(
                "BOARD",
                game_id="g1",
                board=[["X", "", ""], ["", "", ""], ["", "", ""]],
                turn="O",
                revision=1,
            )
        )
        self.assertEqual(state.board[0][0], "X")
        self.assertEqual(state.revision, 1)
        self.assertFalse(state.can_play(0, 1))

    def test_rejected_move_preserves_board_and_allows_retry(self) -> None:
        state = self.identified_state()
        self.start_match(state)
        before = [row[:] for row in state.board]
        state.mark_move_sent(1, 1)
        state.apply_server_message(
            make_message(
                "MOVE_RESULT",
                game_id="g1",
                status="REJECTED",
                code="OCCUPIED",
                message="Posição já ocupada",
            )
        )
        self.assertEqual(state.board, before)
        self.assertIsNone(state.pending_move)
        self.assertTrue(state.can_play(1, 1))

    def test_revision_and_game_id_are_checked(self) -> None:
        state = self.identified_state()
        self.start_match(state)
        with self.assertRaises(ClientStateError):
            state.apply_server_message(
                make_message(
                    "BOARD",
                    game_id="g1",
                    board=[["X", "", ""], ["", "", ""], ["", "", ""]],
                    turn="O",
                    revision=2,
                )
            )
        with self.assertRaises(ClientStateError):
            state.apply_server_message(
                make_message(
                    "GAME_OVER",
                    game_id="g2",
                    result="DRAW",
                    winner=None,
                )
            )

    def test_game_over_enables_new_join_phase(self) -> None:
        state = self.identified_state()
        self.start_match(state)
        state.apply_server_message(
            make_message(
                "GAME_OVER",
                game_id="g1",
                result="ABORTED",
                winner=None,
                reason="OPPONENT_LEFT",
            )
        )
        self.assertEqual(state.phase, ClientPhase.ENDED)
        state.prepare_rejoin()
        self.assertEqual(state.phase, ClientPhase.WAITING)


class TransportTelemetryTests(unittest.TestCase):
    def test_real_channel_reports_wire_size_and_payload(self) -> None:
        receiver_socket, sender_socket = socket.socketpair()
        events: list[TraceEvent] = []
        sender = MessageChannel(
            sender_socket,
            trace_observer=events.append,
            trace_actor="sender",
        )
        receiver = MessageChannel(
            receiver_socket,
            trace_observer=events.append,
            trace_actor="receiver",
        )
        message = make_message("HELLO")
        try:
            sender.send_message(message)
            self.assertEqual(receiver.receive_message(), message)
        finally:
            sender.close()
            receiver.close()

        self.assertEqual([event.direction for event in events], ["SAIDA", "ENTRADA"])
        self.assertTrue(all(event.layer == "TRANSPORTE" for event in events))
        self.assertTrue(all(event.payload == message for event in events))
        self.assertTrue(all(event.byte_count == len(encode_message(message)) for event in events))

    def test_broken_observer_never_breaks_transport(self) -> None:
        receiver_socket, sender_socket = socket.socketpair()

        def broken(_event: TraceEvent) -> None:
            raise RuntimeError("falha apenas na visualização")

        sender = MessageChannel(sender_socket, trace_observer=broken)
        receiver = MessageChannel(receiver_socket, trace_observer=broken)
        try:
            sender.send_message(make_message("PING"))
            self.assertEqual(receiver.receive_message()["type"], "PING")
        finally:
            sender.close()
            receiver.close()


class ServerObservabilityTests(unittest.TestCase):
    def test_server_reports_application_and_transport_without_changing_protocol(self) -> None:
        events: list[TraceEvent] = []
        lock = threading.Lock()

        def observe(event: TraceEvent) -> None:
            with lock:
                events.append(event)

        server = GameServer("127.0.0.1", 0, trace_observer=observe)
        host, port = server.start()
        client = connect_to_server(host, port, timeout=2)
        client.set_timeout(2)
        try:
            client.send_message(make_message("HELLO"))
            welcome = client.receive_message()
            self.assertEqual(welcome["type"], "WELCOME")
            client.send_message(make_message("JOIN"))
            self.assertEqual(client.receive_message()["type"], "WAITING")
            snapshot = server.status_snapshot()
            self.assertEqual(snapshot["session_count"], 1)
            self.assertEqual(snapshot["waiting_count"], 1)
        finally:
            client.close()
            server.stop()

        with lock:
            layers = {event.layer for event in events}
            message_types = {event.message_type for event in events}
        self.assertEqual(layers, {"APLICACAO", "TRANSPORTE"})
        self.assertTrue({"HELLO", "WELCOME", "JOIN", "WAITING"} <= message_types)

    def test_status_snapshot_exposes_authoritative_game_summary(self) -> None:
        server = GameServer("127.0.0.1", 0)
        host, port = server.start()
        first = connect_to_server(host, port, timeout=2)
        second = connect_to_server(host, port, timeout=2)
        first.set_timeout(2)
        second.set_timeout(2)
        try:
            for channel in (first, second):
                channel.send_message(make_message("HELLO"))
                self.assertEqual(channel.receive_message()["type"], "WELCOME")
            first.send_message(make_message("JOIN"))
            self.assertEqual(first.receive_message()["type"], "WAITING")
            second.send_message(make_message("JOIN"))
            first_start = first.receive_message()
            first_board = first.receive_message()
            second_start = second.receive_message()
            second_board = second.receive_message()
            self.assertEqual(first_start["type"], "START")
            self.assertEqual(first_board["type"], "BOARD")
            self.assertEqual(second_start["type"], "START")
            self.assertEqual(second_board["type"], "BOARD")

            snapshot = server.status_snapshot()
            self.assertEqual(
                snapshot["games"],
                [
                    {
                        "game_id": first_start["game_id"],
                        "revision": 0,
                        "turn": "X",
                        "status": "ATIVA",
                    }
                ],
            )
        finally:
            first.close()
            second.close()
            server.stop()


if __name__ == "__main__":
    unittest.main()

