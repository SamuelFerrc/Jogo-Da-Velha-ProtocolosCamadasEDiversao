import socket
import subprocess
import sys
import time
import unittest

from shared.protocol import make_message
from shared.transport import connect_to_server
from tools.traffic_demo import run_demo


class TrafficDemoTests(unittest.TestCase):
    def test_demo_exchanges_expected_messages_over_tcp(self) -> None:
        transcript = run_demo(port=0, delay=0)
        observed_types = [message_type for _, message_type in transcript]

        self.assertEqual(observed_types.count("HELLO"), 2)
        self.assertEqual(observed_types.count("WELCOME"), 2)
        self.assertEqual(observed_types.count("PING"), 2)
        self.assertEqual(observed_types.count("PONG"), 2)
        self.assertEqual(observed_types.count("QUIT"), 2)


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


class ServerProcessTests(unittest.TestCase):
    """Servidor em processo separado (python -m server.server) e dois clientes TCP."""

    def setUp(self) -> None:
        self.port = _free_port()
        self.process = subprocess.Popen(
            [sys.executable, "-m", "server.server", "--port", str(self.port)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        deadline = time.monotonic() + 10
        while True:
            try:
                socket.create_connection(("127.0.0.1", self.port), timeout=0.5).close()
                break
            except OSError:
                if time.monotonic() > deadline:
                    self.fail("servidor não iniciou")
                time.sleep(0.1)

    def tearDown(self) -> None:
        self.process.terminate()
        self.process.wait(timeout=10)

    def test_full_game_between_two_client_processes_view(self) -> None:
        x = connect_to_server("127.0.0.1", self.port, timeout=5)
        o = connect_to_server("127.0.0.1", self.port, timeout=5)
        try:
            for channel in (x, o):
                channel.set_timeout(5)
                channel.send_message(make_message("HELLO"))
                self.assertEqual(channel.receive_message()["type"], "WELCOME")
                channel.send_message(make_message("JOIN"))
                if channel is x:
                    self.assertEqual(x.receive_message()["type"], "WAITING")
            start_x, start_o = x.receive_message(), o.receive_message()
            self.assertEqual((start_x["mark"], start_o["mark"]), ("X", "O"))
            game_id = start_x["game_id"]
            self.assertEqual(game_id, start_o["game_id"])
            self.assertEqual(x.receive_message()["revision"], 0)
            self.assertEqual(o.receive_message()["revision"], 0)

            moves = [(x, 0, 0), (o, 1, 0), (x, 0, 1), (o, 1, 1), (x, 0, 2)]
            for channel, row, col in moves:
                channel.send_message(make_message("MOVE", game_id=game_id, row=row, col=col))
                self.assertEqual(channel.receive_message()["status"], "ACCEPTED")
                for peer in (x, o):
                    self.assertEqual(peer.receive_message()["type"], "BOARD")
            for peer in (x, o):
                over = peer.receive_message()
                self.assertEqual((over["type"], over["result"], over["winner"]), ("GAME_OVER", "WIN", "X"))
        finally:
            x.close()
            o.close()


if __name__ == "__main__":
    unittest.main()
