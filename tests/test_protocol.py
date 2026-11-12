import json
import unittest

import shared
from shared.protocol import (
    CLIENT_TO_SERVER_TYPES,
    ERROR_CODES,
    MAX_MESSAGE_BYTES,
    MESSAGE_TYPES,
    MOVE_REJECTION_CODES,
    SERVER_TO_CLIENT_TYPES,
    InvalidDirectionError,
    InvalidEnvelopeError,
    InvalidPayloadError,
    MessageDecodingError,
    MessageTooLargeError,
    UnknownMessageTypeError,
    UnsupportedVersionError,
    decode_message,
    encode_message,
    make_message,
    validate_client_message,
    validate_payload,
    validate_server_message,
)


class ProtocolBaseTests(unittest.TestCase):
    def test_encode_message_uses_compact_utf8_and_lf(self) -> None:
        encoded = encode_message(
            {
                "type": "ERROR",
                "version": 1,
                "code": "BAD_FORMAT",
                "message": "Posição inválida",
            }
        )

        self.assertEqual(
            encoded,
            (
                '{"type":"ERROR","version":1,"code":"BAD_FORMAT",'
                '"message":"Posição inválida"}\n'
            ).encode("utf-8"),
        )

    def test_decode_message_returns_object(self) -> None:
        message = decode_message(b'{"version":1,"type":"HELLO"}')
        self.assertEqual(message, {"version": 1, "type": "HELLO"})

    def test_encode_rejects_message_above_limit(self) -> None:
        payload = {
            "type": "ERROR",
            "version": 1,
            "code": "BAD_FORMAT",
            "message": "x" * 5000,
        }
        with self.assertRaises(MessageTooLargeError):
            encode_message(payload)

    def test_exact_limit_is_accepted(self) -> None:
        payload = {
            "type": "ERROR",
            "version": 1,
            "code": "BAD_FORMAT",
            "message": "",
        }
        base_size = len(encode_message(payload))
        payload["message"] = "x" * (MAX_MESSAGE_BYTES - base_size)

        encoded = encode_message(payload)

        self.assertEqual(len(encoded), MAX_MESSAGE_BYTES)

    def test_decode_rejects_invalid_utf8(self) -> None:
        with self.assertRaises(MessageDecodingError):
            decode_message(b"\xff")

    def test_decode_rejects_invalid_json(self) -> None:
        with self.assertRaises(MessageDecodingError):
            decode_message(b'{"type":"HELLO",')

    def test_decode_rejects_non_object_root(self) -> None:
        with self.assertRaises(MessageDecodingError):
            decode_message(b"[]")

    def test_decode_rejects_nonstandard_json_constants(self) -> None:
        with self.assertRaises(MessageDecodingError):
            decode_message(
                b'{"type":"ERROR","version":1,"code":"BAD_FORMAT",'
                b'"message":NaN}'
            )

    def test_decode_rejects_duplicate_fields(self) -> None:
        with self.assertRaises(MessageDecodingError):
            decode_message(b'{"type":"HELLO","type":"JOIN","version":1}')

    def test_envelope_requires_uppercase_type(self) -> None:
        with self.assertRaises(InvalidEnvelopeError):
            encode_message({"type": "hello", "version": 1})

    def test_envelope_rejects_boolean_version(self) -> None:
        with self.assertRaises(InvalidEnvelopeError):
            encode_message({"type": "HELLO", "version": True})

    def test_envelope_reports_unsupported_integer_version(self) -> None:
        with self.assertRaises(UnsupportedVersionError):
            encode_message({"type": "HELLO", "version": 2})

    def test_encode_rejects_invalid_payload_before_serializing(self) -> None:
        with self.assertRaises(InvalidPayloadError):
            encode_message({"type": "HELLO", "version": 1, "value": object()})

    def test_encoded_payload_is_valid_json_before_lf(self) -> None:
        encoded = encode_message({"type": "HELLO", "version": 1})
        decoded = json.loads(encoded[:-1].decode("utf-8"))
        self.assertEqual(decoded["type"], "HELLO")


class PayloadValidationTests(unittest.TestCase):
    def test_catalog_contains_exact_message_types(self) -> None:
        self.assertEqual(
            MESSAGE_TYPES,
            {
                "HELLO",
                "WELCOME",
                "JOIN",
                "WAITING",
                "START",
                "MOVE",
                "MOVE_RESULT",
                "BOARD",
                "GAME_OVER",
                "ERROR",
                "PING",
                "PONG",
                "QUIT",
            },
        )

    def test_canonical_messages_are_valid(self) -> None:
        messages = [
            {"type": "HELLO", "version": 1},
            {"type": "WELCOME", "version": 1, "client_id": "c42"},
            {"type": "JOIN", "version": 1},
            {"type": "WAITING", "version": 1},
            {
                "type": "START",
                "version": 1,
                "game_id": "g17",
                "mark": "X",
                "first_turn": "X",
            },
            {
                "type": "MOVE",
                "version": 1,
                "game_id": "g17",
                "row": 1,
                "col": 2,
            },
            {
                "type": "MOVE_RESULT",
                "version": 1,
                "game_id": "g17",
                "status": "ACCEPTED",
                "row": 1,
                "col": 2,
                "revision": 1,
            },
            {
                "type": "MOVE_RESULT",
                "version": 1,
                "game_id": "g17",
                "status": "REJECTED",
                "code": "OCCUPIED",
                "message": "Posição já ocupada",
            },
            {
                "type": "BOARD",
                "version": 1,
                "game_id": "g17",
                "board": [["", "", ""], ["", "", ""], ["", "", ""]],
                "turn": "X",
                "revision": 0,
            },
            {
                "type": "GAME_OVER",
                "version": 1,
                "game_id": "g17",
                "result": "WIN",
                "winner": "X",
            },
            {
                "type": "GAME_OVER",
                "version": 1,
                "game_id": "g17",
                "result": "DRAW",
                "winner": None,
            },
            {
                "type": "GAME_OVER",
                "version": 1,
                "game_id": "g17",
                "result": "ABORTED",
                "winner": None,
                "reason": "OPPONENT_LEFT",
            },
            {
                "type": "ERROR",
                "version": 1,
                "code": "BAD_FORMAT",
                "message": "Mensagem inválida",
            },
            {"type": "PING", "version": 1},
            {"type": "PONG", "version": 1},
            {"type": "QUIT", "version": 1},
        ]

        for message in messages:
            with self.subTest(message_type=message["type"]):
                validate_payload(message)
                self.assertEqual(decode_message(encode_message(message)[:-1]), message)

    def test_unknown_type_has_specific_exception(self) -> None:
        with self.assertRaises(UnknownMessageTypeError):
            validate_payload({"type": "OTHER", "version": 1})

    def test_unexpected_and_missing_fields_are_rejected(self) -> None:
        with self.assertRaises(InvalidPayloadError):
            validate_payload({"type": "HELLO", "version": 1, "extra": True})
        with self.assertRaises(InvalidPayloadError):
            validate_payload({"type": "WELCOME", "version": 1})

    def test_move_rejects_boolean_fractional_and_list_coordinates(self) -> None:
        for row in (True, 1.5, [1]):
            with self.subTest(row=row), self.assertRaises(InvalidPayloadError):
                validate_payload(
                    {
                        "type": "MOVE",
                        "version": 1,
                        "game_id": "g1",
                        "row": row,
                        "col": 0,
                    }
                )

    def test_move_range_is_left_for_semantic_validation(self) -> None:
        validate_payload(
            {
                "type": "MOVE",
                "version": 1,
                "game_id": "g1",
                "row": -1,
                "col": 3,
            }
        )

    def test_move_result_variants_are_exclusive(self) -> None:
        with self.assertRaises(InvalidPayloadError):
            validate_payload(
                {
                    "type": "MOVE_RESULT",
                    "version": 1,
                    "game_id": "g1",
                    "status": "ACCEPTED",
                    "row": 0,
                    "col": 0,
                    "revision": 1,
                    "code": "OCCUPIED",
                }
            )

    def test_rejection_and_error_code_sets_do_not_overlap(self) -> None:
        self.assertTrue(MOVE_REJECTION_CODES.isdisjoint(ERROR_CODES))
        with self.assertRaises(InvalidPayloadError):
            validate_payload(
                {
                    "type": "MOVE_RESULT",
                    "version": 1,
                    "game_id": "g1",
                    "status": "REJECTED",
                    "code": "BAD_FORMAT",
                    "message": "inválida",
                }
            )
        with self.assertRaises(InvalidPayloadError):
            validate_payload(
                {
                    "type": "ERROR",
                    "version": 1,
                    "code": "OCCUPIED",
                    "message": "ocupada",
                }
            )

    def test_board_shape_and_marks_are_validated(self) -> None:
        invalid_boards = [
            [["", "", ""]],
            [["Z", "", ""], ["", "", ""], ["", "", ""]],
        ]
        for board in invalid_boards:
            with self.subTest(board=board), self.assertRaises(InvalidPayloadError):
                validate_payload(
                    {
                        "type": "BOARD",
                        "version": 1,
                        "game_id": "g1",
                        "board": board,
                        "turn": "X",
                        "revision": 0,
                    }
                )

    def test_game_over_conditional_fields_are_enforced(self) -> None:
        with self.assertRaises(InvalidPayloadError):
            validate_payload(
                {
                    "type": "GAME_OVER",
                    "version": 1,
                    "game_id": "g1",
                    "result": "ABORTED",
                    "winner": None,
                }
            )

    def test_client_and_server_directions_are_enforced(self) -> None:
        self.assertIn("PING", CLIENT_TO_SERVER_TYPES)
        self.assertIn("PING", SERVER_TO_CLIENT_TYPES)
        validate_client_message({"type": "HELLO", "version": 1})
        validate_server_message({"type": "WAITING", "version": 1})
        with self.assertRaises(InvalidDirectionError):
            validate_client_message({"type": "WAITING", "version": 1})
        with self.assertRaises(InvalidDirectionError):
            validate_server_message({"type": "JOIN", "version": 1})

    def test_make_message_supplies_version_and_validates(self) -> None:
        self.assertEqual(make_message("PING"), {"type": "PING", "version": 1})
        with self.assertRaises(InvalidPayloadError):
            make_message("WELCOME")


class SharedPublicApiTests(unittest.TestCase):
    def test_client_and_server_can_import_stable_shared_api(self) -> None:
        expected_names = {
            "MessageChannel",
            "connect_to_server",
            "create_listening_socket",
            "accept_connection",
            "send_message",
            "receive_message",
            "close_connection",
            "validate_client_message",
            "validate_server_message",
            "make_message",
            "send_ping",
            "handle_heartbeat_message",
        }

        self.assertTrue(expected_names.issubset(set(shared.__all__)))
        for name in expected_names:
            self.assertTrue(callable(getattr(shared, name)))


if __name__ == "__main__":
    unittest.main()
