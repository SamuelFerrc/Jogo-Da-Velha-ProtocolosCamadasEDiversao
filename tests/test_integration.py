import unittest

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


if __name__ == "__main__":
    unittest.main()
