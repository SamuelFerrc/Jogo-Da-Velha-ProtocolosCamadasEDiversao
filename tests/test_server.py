"""Testes do servidor TCP com sockets de loopback."""

import json
import socket
import threading
import unittest

from server.server import GameServer
from shared.protocol import make_message
from shared.transport import (
    ConnectionClosedError,
    MessageChannel,
    TransportError,
    connect_to_server,
)

TIMEOUT = 5.0


class ServerTestCase(unittest.TestCase):
    handshake_timeout: float | None = 30.0

    def setUp(self) -> None:
        self.server = GameServer("127.0.0.1", 0, handshake_timeout=self.handshake_timeout)
        self.host, self.port = self.server.start()
        self.channels: list[MessageChannel] = []

    def tearDown(self) -> None:
        for channel in self.channels:
            channel.close()
        self.server.stop()

    def connect(self) -> MessageChannel:
        channel = connect_to_server(self.host, self.port, timeout=TIMEOUT)
        channel.set_timeout(TIMEOUT)
        self.channels.append(channel)
        return channel

    def expect(self, channel: MessageChannel, message_type: str, **fields) -> dict:
        message = channel.receive_message()
        self.assertEqual(message["type"], message_type, message)
        for key, value in fields.items():
            self.assertEqual(message[key], value, message)
        return message

    def identify(self) -> MessageChannel:
        channel = self.connect()
        channel.send_message(make_message("HELLO"))
        self.expect(channel, "WELCOME")
        return channel

    def start_match(self) -> tuple[MessageChannel, MessageChannel, str]:
        """Devolve (jogador X, jogador O, game_id) já com START e BOARD inicial lidos."""

        first = self.identify()
        first.send_message(make_message("JOIN"))
        self.expect(first, "WAITING")
        second = self.identify()
        second.send_message(make_message("JOIN"))
        start_x = self.expect(first, "START", mark="X", first_turn="X")
        start_o = self.expect(second, "START", mark="O", first_turn="X")
        self.assertEqual(start_x["game_id"], start_o["game_id"])
        game_id = start_x["game_id"]
        for channel in (first, second):
            self.expect(channel, "BOARD", game_id=game_id, turn="X", revision=0)
        return first, second, game_id

    def move(self, channel: MessageChannel, game_id: str, row, col) -> None:
        channel.send_message(
            {"type": "MOVE", "version": 1, "game_id": game_id, "row": row, "col": col}
        )

    def play_accepted(self, mover, other, game_id, row, col, revision) -> None:
        self.move(mover, game_id, row, col)
        self.expect(mover, "MOVE_RESULT", status="ACCEPTED", row=row, col=col, revision=revision)
        for channel in (mover, other):
            self.expect(channel, "BOARD", revision=revision)


class HandshakeAndLobbyTests(ServerTestCase):
    def test_hello_welcome_and_unique_client_ids(self) -> None:
        ids = set()
        for _ in range(3):
            channel = self.connect()
            channel.send_message(make_message("HELLO"))
            ids.add(self.expect(channel, "WELCOME")["client_id"])
        self.assertEqual(len(ids), 3)

    def test_join_waits_then_pairs_with_distinct_marks_and_initial_board(self) -> None:
        self.start_match()

    def test_two_pairs_get_distinct_games(self) -> None:
        _, _, game_a = self.start_match()
        _, _, game_b = self.start_match()
        self.assertNotEqual(game_a, game_b)

    def test_join_before_hello_is_invalid_state(self) -> None:
        channel = self.connect()
        channel.send_message(make_message("JOIN"))
        self.expect(channel, "ERROR", code="INVALID_STATE")
        channel.send_message(make_message("HELLO"))
        self.expect(channel, "WELCOME")

    def test_duplicate_hello_and_join_are_invalid_state(self) -> None:
        channel = self.identify()
        channel.send_message(make_message("HELLO"))
        self.expect(channel, "ERROR", code="INVALID_STATE")
        channel.send_message(make_message("JOIN"))
        self.expect(channel, "WAITING")
        channel.send_message(make_message("JOIN"))
        self.expect(channel, "ERROR", code="INVALID_STATE")

    def test_ping_gets_pong(self) -> None:
        channel = self.identify()
        channel.send_message(make_message("PING"))
        self.expect(channel, "PONG")

    def test_waiting_client_that_leaves_is_not_paired(self) -> None:
        ghost = self.identify()
        ghost.send_message(make_message("JOIN"))
        self.expect(ghost, "WAITING")
        ghost.close()
        # Aguarda o servidor limpar a fila.
        for _ in range(100):
            if self.server._lobby.waiting_count() == 0:
                break
            threading.Event().wait(0.02)
        live = self.identify()
        live.send_message(make_message("JOIN"))
        self.expect(live, "WAITING")


class ProtocolErrorTests(ServerTestCase):
    def send_raw(self, channel: MessageChannel, data: bytes) -> None:
        channel.socket.sendall(data)

    def test_bad_format_keeps_session(self) -> None:
        channel = self.identify()
        for raw in (b"isto nao e json\n", b"[1,2]\n", b'{"type":"MOVE","version":1}\n',
                    b'{"type":"JOIN"}\n', b"\xff\xfe\n"):
            self.send_raw(channel, raw)
            self.expect(channel, "ERROR", code="BAD_FORMAT")
        channel.send_message(make_message("JOIN"))
        self.expect(channel, "WAITING")

    def test_unknown_type(self) -> None:
        channel = self.identify()
        self.send_raw(channel, b'{"type":"FOO","version":1}\n')
        self.expect(channel, "ERROR", code="UNKNOWN_TYPE")

    def test_server_only_type_from_client_is_rejected(self) -> None:
        channel = self.identify()
        self.send_raw(channel, b'{"type":"WAITING","version":1}\n')
        self.expect(channel, "ERROR", code="BAD_FORMAT")

    def test_unsupported_version_closes_connection(self) -> None:
        channel = self.connect()
        self.send_raw(channel, b'{"type":"HELLO","version":2}\n')
        self.expect(channel, "ERROR", code="UNSUPPORTED_VERSION")
        with self.assertRaises(ConnectionClosedError):
            channel.receive_message()

    def test_message_too_large_closes_connection(self) -> None:
        channel = self.connect()
        self.send_raw(channel, b"x" * 5000)
        self.expect(channel, "ERROR", code="MESSAGE_TOO_LARGE")
        with self.assertRaises(TransportError):
            channel.receive_message()

    def test_fragmented_and_concatenated_messages(self) -> None:
        channel = self.connect()
        self.send_raw(channel, b'{"type":"HEL')
        threading.Event().wait(0.05)
        self.send_raw(channel, b'LO","version":1}\n{"type":"JOIN","version":1}\n')
        self.expect(channel, "WELCOME")
        self.expect(channel, "WAITING")

    def test_move_outside_game_is_rejected_not_error(self) -> None:
        channel = self.identify()
        self.move(channel, "g1", 0, 0)
        self.expect(channel, "MOVE_RESULT", status="REJECTED", code="NOT_IN_GAME")

    def test_quit_closes_session(self) -> None:
        channel = self.identify()
        channel.send_message(make_message("QUIT"))
        with self.assertRaises(ConnectionClosedError):
            channel.receive_message()


class HandshakeTimeoutTests(ServerTestCase):
    handshake_timeout = 0.3

    def test_silent_client_is_dropped(self) -> None:
        channel = self.connect()
        with self.assertRaises(ConnectionClosedError):
            channel.receive_message()


class GameplayTests(ServerTestCase):
    def test_x_wins_full_game(self) -> None:
        x, o, game_id = self.start_match()
        self.play_accepted(x, o, game_id, 0, 0, 1)
        self.play_accepted(o, x, game_id, 1, 0, 2)
        self.play_accepted(x, o, game_id, 0, 1, 3)
        self.play_accepted(o, x, game_id, 1, 1, 4)
        self.move(x, game_id, 0, 2)
        self.expect(x, "MOVE_RESULT", status="ACCEPTED", revision=5)
        for channel in (x, o):
            self.expect(channel, "BOARD", revision=5, turn=None)
            self.expect(channel, "GAME_OVER", result="WIN", winner="X")
        self.move(o, game_id, 2, 2)
        self.expect(o, "MOVE_RESULT", status="REJECTED", code="GAME_FINISHED")

    def test_o_wins(self) -> None:
        x, o, g = self.start_match()
        for mover, other, r, c, rev in [
            (x, o, 0, 0, 1), (o, x, 1, 0, 2), (x, o, 0, 1, 3), (o, x, 1, 1, 4), (x, o, 2, 2, 5),
        ]:
            self.play_accepted(mover, other, g, r, c, rev)
        self.move(o, g, 1, 2)
        self.expect(o, "MOVE_RESULT", status="ACCEPTED", revision=6)
        for channel in (x, o):
            self.expect(channel, "BOARD", revision=6, turn=None)
            self.expect(channel, "GAME_OVER", result="WIN", winner="O")

    def test_draw(self) -> None:
        x, o, g = self.start_match()
        seq = [(0, 0), (0, 1), (0, 2), (1, 1), (1, 0), (1, 2), (2, 1), (2, 0)]
        for i, (r, c) in enumerate(seq):
            mover, other = (x, o) if i % 2 == 0 else (o, x)
            self.play_accepted(mover, other, g, r, c, i + 1)
        self.move(x, g, 2, 2)
        self.expect(x, "MOVE_RESULT", status="ACCEPTED", revision=9)
        for channel in (x, o):
            self.expect(channel, "BOARD", revision=9, turn=None)
            self.expect(channel, "GAME_OVER", result="DRAW", winner=None)

    def test_rejections_do_not_change_state_and_send_only_move_result(self) -> None:
        x, o, g = self.start_match()
        self.move(o, g, 0, 0)  # fora do turno
        self.expect(o, "MOVE_RESULT", status="REJECTED", code="NOT_YOUR_TURN")
        self.play_accepted(x, o, g, 0, 0, 1)
        self.move(x, g, 1, 1)  # duas jogadas seguidas
        self.expect(x, "MOVE_RESULT", status="REJECTED", code="NOT_YOUR_TURN")
        self.move(o, g, 0, 0)  # ocupada
        self.expect(o, "MOVE_RESULT", status="REJECTED", code="OCCUPIED")
        self.move(o, g, -1, 0)
        self.expect(o, "MOVE_RESULT", status="REJECTED", code="INVALID_POSITION")
        self.move(o, g, 0, 3)
        self.expect(o, "MOVE_RESULT", status="REJECTED", code="INVALID_POSITION")
        self.move(o, "g999", 1, 1)  # game_id alheio
        self.expect(o, "MOVE_RESULT", status="REJECTED", code="NOT_IN_GAME")
        # Estado intacto: a próxima jogada válida ainda é a revisão 2.
        self.play_accepted(o, x, g, 1, 1, 2)

    def test_wrong_types_are_bad_format(self) -> None:
        x, o, g = self.start_match()
        for row in (True, 1.5, "1", [1], None):
            raw = {"type": "MOVE", "version": 1, "game_id": g, "row": row, "col": 0}
            x.socket.sendall(json.dumps(raw).encode() + b"\n")
            self.expect(x, "ERROR", code="BAD_FORMAT")
        self.play_accepted(x, o, g, 0, 0, 1)

    def test_opponent_quit_aborts_game(self) -> None:
        x, o, g = self.start_match()
        x.send_message(make_message("QUIT"))
        self.expect(o, "GAME_OVER", result="ABORTED", winner=None, reason="OPPONENT_LEFT")
        self.move(o, g, 0, 0)
        self.expect(o, "MOVE_RESULT", status="REJECTED", code="GAME_FINISHED")

    def test_opponent_socket_drop_aborts_game(self) -> None:
        x, o, _ = self.start_match()
        o.socket.shutdown(socket.SHUT_RDWR)
        o.close()
        self.expect(x, "GAME_OVER", result="ABORTED", reason="OPPONENT_LEFT")

    def test_quit_after_game_over_sends_no_abort(self) -> None:
        x, o, g = self.start_match()
        for mover, other, r, c, rev in [
            (x, o, 0, 0, 1), (o, x, 1, 0, 2), (x, o, 0, 1, 3), (o, x, 1, 1, 4),
        ]:
            self.play_accepted(mover, other, g, r, c, rev)
        self.move(x, g, 0, 2)
        self.expect(x, "MOVE_RESULT")
        self.expect(x, "BOARD")
        self.expect(x, "GAME_OVER", result="WIN")
        self.expect(o, "BOARD")
        self.expect(o, "GAME_OVER", result="WIN")
        x.send_message(make_message("QUIT"))
        o.set_timeout(0.3)
        with self.assertRaises(Exception) as ctx:
            o.receive_message()
        self.assertNotIn("ABORTED", str(ctx.exception))

    def test_rematch_via_join_on_same_connection(self) -> None:
        x, o, g = self.start_match()
        for mover, other, r, c, rev in [
            (x, o, 0, 0, 1), (o, x, 1, 0, 2), (x, o, 0, 1, 3), (o, x, 1, 1, 4),
        ]:
            self.play_accepted(mover, other, g, r, c, rev)
        self.move(x, g, 0, 2)
        for channel in (x, o):
            if channel is x:
                self.expect(x, "MOVE_RESULT")
            self.expect(channel, "BOARD")
            self.expect(channel, "GAME_OVER")
        x.send_message(make_message("JOIN"))
        self.expect(x, "WAITING")
        o.send_message(make_message("JOIN"))
        start_x = self.expect(x, "START")
        start_o = self.expect(o, "START")
        self.assertNotEqual(start_x["game_id"], g)
        self.assertEqual(start_x["game_id"], start_o["game_id"])
        self.assertNotEqual(start_x["mark"], start_o["mark"])
        self.expect(x, "BOARD", revision=0)
        self.expect(o, "BOARD", revision=0)

    def test_concurrent_moves_produce_single_acceptance(self) -> None:
        x, o, g = self.start_match()
        barrier = threading.Barrier(2)

        def attempt(row: int) -> None:
            barrier.wait()
            self.move(x, g, row, 0)

        threads = [threading.Thread(target=attempt, args=(r,)) for r in (0, 1)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        received = [x.receive_message() for _ in range(3)]
        statuses = sorted(m["status"] for m in received if m["type"] == "MOVE_RESULT")
        self.assertEqual(statuses, ["ACCEPTED", "REJECTED"])
        self.assertEqual([m["type"] for m in received].count("BOARD"), 1)
        self.expect(o, "BOARD", revision=1, turn="O")
        self.play_accepted(o, x, g, 2, 2, 2)

    def test_sequential_matches_do_not_interfere(self) -> None:
        errors: list[BaseException] = []

        def run() -> None:
            try:
                x, o, g = self.start_match()
                self.play_accepted(x, o, g, 0, 0, 1)
            except BaseException as exc:  # noqa: BLE001
                errors.append(exc)

        for _ in range(5):
            run()
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
