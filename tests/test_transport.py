import json
import socket
import threading
import time
import unittest
from unittest import mock

from shared.protocol import (
    MAX_MESSAGE_BYTES,
    MessageDecodingError,
    MessageTooLargeError,
    encode_message,
)
from shared.transport import (
    ConnectionClosedError,
    MessageChannel,
    SocketOperationError,
    TransportTimeoutError,
    accept_connection,
    close_connection,
    connect_to_server,
    create_listening_socket,
    handle_heartbeat_message,
    receive_message,
    send_message,
    send_ping,
)


class ScriptedSocket:
    def __init__(self, chunks: list[bytes | BaseException] | None = None) -> None:
        self.chunks = list(chunks or [])
        self.sent = bytearray()
        self.recv_calls = 0
        self.shutdown_calls = 0
        self.close_calls = 0
        self.timeout: float | None = None

    def recv(self, size: int) -> bytes:
        self.recv_calls += 1
        if not self.chunks:
            return b""
        result = self.chunks.pop(0)
        if isinstance(result, BaseException):
            raise result
        if len(result) > size:
            self.chunks.insert(0, result[size:])
            return result[:size]
        return result

    def sendall(self, data: bytes) -> None:
        self.sent.extend(data)

    def shutdown(self, how: int) -> None:
        self.shutdown_calls += 1

    def close(self) -> None:
        self.close_calls += 1

    def settimeout(self, timeout: float | None) -> None:
        self.timeout = timeout

    def gettimeout(self) -> float | None:
        return self.timeout


class SlowByteSocket(ScriptedSocket):
    def sendall(self, data: bytes) -> None:
        for byte in data:
            self.sent.append(byte)
            time.sleep(0.00001)


class FailingSendSocket(ScriptedSocket):
    def sendall(self, data: bytes) -> None:
        raise OSError("socket quebrado")


class TimeoutSendSocket(ScriptedSocket):
    def sendall(self, data: bytes) -> None:
        raise socket.timeout("expirou")


class TransportBaseTests(unittest.TestCase):
    def test_fragmented_message_is_reassembled(self) -> None:
        raw = ScriptedSocket(
            [b'{"type":"HEL', b'LO","version":', b"1}\n"]
        )
        channel = MessageChannel(raw)  # type: ignore[arg-type]

        message = channel.receive_message()

        self.assertEqual(message["type"], "HELLO")
        self.assertEqual(raw.recv_calls, 3)

    def test_concatenated_messages_preserve_residual_buffer(self) -> None:
        raw = ScriptedSocket(
            [
                encode_message({"type": "HELLO", "version": 1})
                + encode_message({"type": "JOIN", "version": 1})
            ]
        )
        channel = MessageChannel(raw)  # type: ignore[arg-type]

        first = channel.receive_message()
        second = channel.receive_message()

        self.assertEqual(first["type"], "HELLO")
        self.assertEqual(second["type"], "JOIN")
        self.assertEqual(raw.recv_calls, 1)
        self.assertEqual(channel.buffered_bytes, 0)

    def test_raw_socket_wrappers_reuse_the_same_buffer(self) -> None:
        raw = ScriptedSocket(
            [
                encode_message({"type": "HELLO", "version": 1})
                + encode_message({"type": "JOIN", "version": 1})
            ]
        )

        first = receive_message(raw)  # type: ignore[arg-type]
        second = receive_message(raw)  # type: ignore[arg-type]

        self.assertEqual((first["type"], second["type"]), ("HELLO", "JOIN"))
        self.assertEqual(raw.recv_calls, 1)

    def test_eof_is_not_an_empty_message(self) -> None:
        channel = MessageChannel(ScriptedSocket([b""]))  # type: ignore[arg-type]
        with self.assertRaises(ConnectionClosedError):
            channel.receive_message()
        self.assertTrue(channel.closed)

    def test_receive_timeout_is_translated(self) -> None:
        channel = MessageChannel(  # type: ignore[arg-type]
            ScriptedSocket([socket.timeout("expirou")])
        )
        with self.assertRaises(TransportTimeoutError):
            channel.receive_message()
        self.assertFalse(channel.closed)

    def test_partial_buffer_survives_receive_timeout(self) -> None:
        raw = ScriptedSocket(
            [b'{"type":"HEL', socket.timeout("expirou"), b'LO","version":1}\n']
        )
        channel = MessageChannel(raw)  # type: ignore[arg-type]

        with self.assertRaises(TransportTimeoutError):
            channel.receive_message()
        message = channel.receive_message()

        self.assertEqual(message["type"], "HELLO")
        self.assertFalse(channel.closed)

    def test_receive_socket_error_is_translated(self) -> None:
        channel = MessageChannel(ScriptedSocket([OSError("falha")]))  # type: ignore[arg-type]
        with self.assertRaises(SocketOperationError):
            channel.receive_message()
        self.assertTrue(channel.closed)

    def test_send_socket_error_is_translated(self) -> None:
        channel = MessageChannel(FailingSendSocket())  # type: ignore[arg-type]
        with self.assertRaises(SocketOperationError):
            channel.send_message({"type": "HELLO", "version": 1})
        self.assertTrue(channel.closed)

    def test_send_timeout_is_translated(self) -> None:
        channel = MessageChannel(TimeoutSendSocket())  # type: ignore[arg-type]
        with self.assertRaises(TransportTimeoutError):
            channel.send_message({"type": "HELLO", "version": 1})
        self.assertTrue(channel.closed)

    def test_connect_timeout_is_translated(self) -> None:
        with mock.patch(
            "shared.transport.socket.create_connection",
            side_effect=socket.timeout("expirou"),
        ):
            with self.assertRaises(TransportTimeoutError):
                connect_to_server("127.0.0.1", 5000, timeout=0.01)

    def test_connect_socket_error_is_translated(self) -> None:
        with mock.patch(
            "shared.transport.socket.create_connection",
            side_effect=OSError("falha"),
        ):
            with self.assertRaises(SocketOperationError):
                connect_to_server("127.0.0.1", 5000, timeout=0.01)

    def test_buffer_without_lf_cannot_grow_past_limit(self) -> None:
        channel = MessageChannel(  # type: ignore[arg-type]
            ScriptedSocket([b"x" * MAX_MESSAGE_BYTES])
        )
        with self.assertRaises(MessageTooLargeError):
            channel.receive_message()

    def test_delimited_record_above_limit_is_rejected(self) -> None:
        channel = MessageChannel(  # type: ignore[arg-type]
            ScriptedSocket([b"x" * MAX_MESSAGE_BYTES + b"\n"])
        )
        with self.assertRaises(MessageTooLargeError):
            channel.receive_message()

    def test_close_is_idempotent(self) -> None:
        raw = ScriptedSocket()
        channel = MessageChannel(raw)  # type: ignore[arg-type]

        channel.close()
        channel.close()

        self.assertTrue(channel.closed)
        self.assertEqual(raw.shutdown_calls, 1)
        self.assertEqual(raw.close_calls, 1)

    def test_send_after_close_is_rejected(self) -> None:
        channel = MessageChannel(ScriptedSocket())  # type: ignore[arg-type]
        channel.close()
        with self.assertRaises(ConnectionClosedError):
            channel.send_message({"type": "HELLO", "version": 1})

    def test_timeout_can_be_configured_and_cleared(self) -> None:
        raw = ScriptedSocket()
        channel = MessageChannel(raw)  # type: ignore[arg-type]

        channel.set_timeout(2.5)
        self.assertEqual(channel.get_timeout(), 2.5)
        channel.set_timeout(None)
        self.assertIsNone(channel.get_timeout())

        with self.assertRaises(ValueError):
            channel.set_timeout(0)

    def test_concurrent_sends_do_not_interleave_records(self) -> None:
        raw = SlowByteSocket()
        channel = MessageChannel(raw)  # type: ignore[arg-type]
        start = threading.Barrier(8)

        def worker(index: int) -> None:
            start.wait()
            channel.send_message(
                {
                    "type": "ERROR",
                    "version": 1,
                    "code": "BAD_FORMAT",
                    "message": str(index),
                }
            )

        threads = [threading.Thread(target=worker, args=(index,)) for index in range(8)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=2)

        self.assertTrue(all(not thread.is_alive() for thread in threads))
        records = bytes(raw.sent).splitlines()
        self.assertEqual(len(records), 8)
        decoded = [json.loads(record) for record in records]
        self.assertEqual({int(item["message"]) for item in decoded}, set(range(8)))

    def test_send_ping_uses_canonical_message(self) -> None:
        raw = ScriptedSocket()
        send_ping(raw)  # type: ignore[arg-type]
        self.assertEqual(
            bytes(raw.sent), encode_message({"type": "PING", "version": 1})
        )

    def test_ping_is_consumed_and_replied_with_pong(self) -> None:
        raw = ScriptedSocket()
        consumed = handle_heartbeat_message(  # type: ignore[arg-type]
            raw, {"type": "PING", "version": 1}
        )
        self.assertTrue(consumed)
        self.assertEqual(
            bytes(raw.sent), encode_message({"type": "PONG", "version": 1})
        )

    def test_pong_is_consumed_without_reply(self) -> None:
        raw = ScriptedSocket()
        consumed = handle_heartbeat_message(  # type: ignore[arg-type]
            raw, {"type": "PONG", "version": 1}
        )
        self.assertTrue(consumed)
        self.assertEqual(bytes(raw.sent), b"")

    def test_non_heartbeat_message_continues_to_application(self) -> None:
        raw = ScriptedSocket()
        consumed = handle_heartbeat_message(  # type: ignore[arg-type]
            raw, {"type": "HELLO", "version": 1}
        )
        self.assertFalse(consumed)
        self.assertEqual(bytes(raw.sent), b"")

    def test_loopback_connect_accept_send_receive_and_close(self) -> None:
        listener = create_listening_socket("127.0.0.1", 0, backlog=1)
        port = listener.getsockname()[1]
        accepted: list[MessageChannel] = []

        def accept_one() -> None:
            channel, _ = accept_connection(listener)
            accepted.append(channel)

        thread = threading.Thread(target=accept_one)
        thread.start()
        client = connect_to_server("127.0.0.1", port, timeout=1)
        thread.join(timeout=2)

        try:
            self.assertEqual(len(accepted), 1)
            send_message(client, {"type": "HELLO", "version": 1})
            self.assertEqual(accepted[0].receive_message()["type"], "HELLO")
        finally:
            close_connection(client)
            if accepted:
                accepted[0].close()
            listener.close()


class RealSocketFramingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.receiver_socket, self.sender_socket = socket.socketpair()
        self.addCleanup(self.receiver_socket.close)
        self.addCleanup(self.sender_socket.close)

    def test_real_socket_reassembles_record_with_small_reads(self) -> None:
        channel = MessageChannel(self.receiver_socket, recv_size=3)
        self.sender_socket.sendall(
            encode_message({"type": "HELLO", "version": 1})
        )

        self.assertEqual(channel.receive_message()["type"], "HELLO")

    def test_real_socket_separates_concatenated_records(self) -> None:
        channel = MessageChannel(self.receiver_socket)
        self.sender_socket.sendall(
            encode_message({"type": "HELLO", "version": 1})
            + encode_message({"type": "JOIN", "version": 1})
        )

        self.assertEqual(channel.receive_message()["type"], "HELLO")
        self.assertEqual(channel.receive_message()["type"], "JOIN")

    def test_real_socket_preserves_unicode(self) -> None:
        channel = MessageChannel(self.receiver_socket, recv_size=7)
        expected = {
            "type": "ERROR",
            "version": 1,
            "code": "BAD_FORMAT",
            "message": "Posição inválida",
        }
        self.sender_socket.sendall(encode_message(expected))

        self.assertEqual(channel.receive_message(), expected)

    def test_real_socket_rejects_invalid_utf8_record(self) -> None:
        channel = MessageChannel(self.receiver_socket)
        self.sender_socket.sendall(b"\xff\n")

        with self.assertRaises(MessageDecodingError) as context:
            channel.receive_message()
        self.assertEqual(context.exception.code, "BAD_FORMAT")

    def test_real_socket_rejects_invalid_json_record(self) -> None:
        channel = MessageChannel(self.receiver_socket)
        self.sender_socket.sendall(b"{]\n")

        with self.assertRaises(MessageDecodingError) as context:
            channel.receive_message()
        self.assertEqual(context.exception.code, "BAD_FORMAT")


if __name__ == "__main__":
    unittest.main()
