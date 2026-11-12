"""Contrato TTTP/1, serialização JSONL e validação independentes de rede."""

from __future__ import annotations

import json
from collections.abc import Iterable
from typing import Any

PROTOCOL_VERSION = 1
MAX_MESSAGE_BYTES = 4096
MESSAGE_DELIMITER = b"\n"

MESSAGE_TYPES = frozenset(
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
    }
)

CLIENT_TO_SERVER_TYPES = frozenset(
    {"HELLO", "JOIN", "MOVE", "QUIT", "PING", "PONG"}
)
SERVER_TO_CLIENT_TYPES = frozenset(
    {
        "WELCOME",
        "WAITING",
        "START",
        "MOVE_RESULT",
        "BOARD",
        "GAME_OVER",
        "ERROR",
        "PING",
        "PONG",
    }
)

MOVE_REJECTION_CODES = frozenset(
    {
        "NOT_IN_GAME",
        "NOT_YOUR_TURN",
        "INVALID_POSITION",
        "OCCUPIED",
        "GAME_FINISHED",
    }
)
ERROR_CODES = frozenset(
    {
        "BAD_FORMAT",
        "UNKNOWN_TYPE",
        "UNSUPPORTED_VERSION",
        "MESSAGE_TOO_LARGE",
        "INVALID_STATE",
        "TIMEOUT",
    }
)

_ENVELOPE_FIELDS = frozenset({"type", "version"})
_MARKS = frozenset({"X", "O"})
_BOARD_CELLS = frozenset({"", "X", "O"})


class ProtocolError(ValueError):
    """Erro base ao codificar ou decodificar uma mensagem TTTP/1."""

    code = "BAD_FORMAT"


class InvalidEnvelopeError(ProtocolError):
    """O objeto não possui um envelope TTTP/1 válido."""


class UnsupportedVersionError(ProtocolError):
    """A mensagem declara uma versão inteira diferente de TTTP/1."""

    code = "UNSUPPORTED_VERSION"


class UnknownMessageTypeError(ProtocolError):
    """O envelope informa um tipo que não pertence ao catálogo TTTP/1."""

    code = "UNKNOWN_TYPE"


class InvalidPayloadError(ProtocolError):
    """Os campos específicos da mensagem não correspondem ao esquema."""


class InvalidDirectionError(ProtocolError):
    """O tipo de mensagem não é permitido na direção informada."""

    code = "INVALID_STATE"


class MessageEncodingError(ProtocolError):
    """O payload não pode ser serializado como JSON TTTP/1."""


class MessageDecodingError(ProtocolError):
    """O registro não contém um objeto JSON UTF-8 válido."""


class MessageTooLargeError(ProtocolError):
    """O registro excede MAX_MESSAGE_BYTES, incluindo o LF."""

    code = "MESSAGE_TOO_LARGE"


def _is_json_integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def validate_envelope(message: dict[str, Any]) -> None:
    """Valida os campos comuns a todas as mensagens TTTP/1.

    A função não valida os campos específicos de cada ``type``. Para a
    validação estrutural completa, use ``validate_payload``.
    """

    if not isinstance(message, dict):
        raise InvalidEnvelopeError("A mensagem deve ser um objeto JSON")

    if not all(isinstance(key, str) for key in message):
        raise InvalidEnvelopeError("Todos os nomes de campos devem ser strings")

    message_type = message.get("type")
    if not isinstance(message_type, str) or not message_type:
        raise InvalidEnvelopeError("O campo 'type' deve ser uma string não vazia")
    if message_type != message_type.upper():
        raise InvalidEnvelopeError("O campo 'type' deve usar grafia maiúscula")

    version = message.get("version")
    if not _is_json_integer(version):
        raise InvalidEnvelopeError("O campo 'version' deve ser um inteiro")
    if version != PROTOCOL_VERSION:
        raise UnsupportedVersionError(
            f"Versão de protocolo não suportada: {version}"
        )


def _require_exact_fields(
    message: dict[str, Any], required_fields: Iterable[str]
) -> None:
    expected = _ENVELOPE_FIELDS | frozenset(required_fields)
    actual = frozenset(message)
    missing = expected - actual
    unexpected = actual - expected
    if missing or unexpected:
        details: list[str] = []
        if missing:
            details.append(f"ausentes: {', '.join(sorted(missing))}")
        if unexpected:
            details.append(f"inesperados: {', '.join(sorted(unexpected))}")
        raise InvalidPayloadError("Campos inválidos (" + "; ".join(details) + ")")


def _require_string(message: dict[str, Any], field: str) -> str:
    value = message[field]
    if not isinstance(value, str):
        raise InvalidPayloadError(f"O campo '{field}' deve ser uma string")
    return value


def _require_integer(message: dict[str, Any], field: str) -> int:
    value = message[field]
    if not _is_json_integer(value):
        raise InvalidPayloadError(f"O campo '{field}' deve ser um inteiro")
    return value


def _require_enum(message: dict[str, Any], field: str, values: set[str] | frozenset[str]) -> str:
    value = _require_string(message, field)
    if value not in values:
        allowed = ", ".join(sorted(values))
        raise InvalidPayloadError(
            f"Valor inválido para '{field}'; permitidos: {allowed}"
        )
    return value


def _validate_board(board: Any) -> None:
    if not isinstance(board, list) or len(board) != 3:
        raise InvalidPayloadError("O campo 'board' deve possuir exatamente 3 linhas")
    for row in board:
        if not isinstance(row, list) or len(row) != 3:
            raise InvalidPayloadError(
                "Cada linha de 'board' deve possuir exatamente 3 células"
            )
        for cell in row:
            if not isinstance(cell, str) or cell not in _BOARD_CELLS:
                raise InvalidPayloadError(
                    "Cada célula de 'board' deve ser 'X', 'O' ou string vazia"
                )


def validate_payload(message: dict[str, Any]) -> None:
    """Valida campos, tipos e enumerações sem aplicar regras do jogo."""

    validate_envelope(message)
    message_type = message["type"]
    if message_type not in MESSAGE_TYPES:
        raise UnknownMessageTypeError(f"Tipo de mensagem desconhecido: {message_type}")

    if message_type in {"HELLO", "JOIN", "WAITING", "PING", "PONG", "QUIT"}:
        _require_exact_fields(message, ())
        return

    if message_type == "WELCOME":
        _require_exact_fields(message, {"client_id"})
        _require_string(message, "client_id")
        return

    if message_type == "START":
        _require_exact_fields(message, {"game_id", "mark", "first_turn"})
        _require_string(message, "game_id")
        _require_enum(message, "mark", _MARKS)
        if _require_string(message, "first_turn") != "X":
            raise InvalidPayloadError("O campo 'first_turn' deve ser 'X'")
        return

    if message_type == "MOVE":
        _require_exact_fields(message, {"game_id", "row", "col"})
        _require_string(message, "game_id")
        _require_integer(message, "row")
        _require_integer(message, "col")
        return

    if message_type == "MOVE_RESULT":
        status = message.get("status")
        if status == "ACCEPTED":
            _require_exact_fields(
                message, {"game_id", "status", "row", "col", "revision"}
            )
            _require_string(message, "game_id")
            row = _require_integer(message, "row")
            col = _require_integer(message, "col")
            revision = _require_integer(message, "revision")
            if row not in range(3) or col not in range(3):
                raise InvalidPayloadError(
                    "MOVE_RESULT aceito deve usar row/col entre 0 e 2"
                )
            if revision < 1:
                raise InvalidPayloadError(
                    "MOVE_RESULT aceito deve possuir revision maior ou igual a 1"
                )
            return
        if status == "REJECTED":
            _require_exact_fields(
                message, {"game_id", "status", "code", "message"}
            )
            _require_string(message, "game_id")
            _require_enum(message, "code", MOVE_REJECTION_CODES)
            _require_string(message, "message")
            return
        raise InvalidPayloadError(
            "O campo 'status' de MOVE_RESULT deve ser 'ACCEPTED' ou 'REJECTED'"
        )

    if message_type == "BOARD":
        _require_exact_fields(message, {"game_id", "board", "turn", "revision"})
        _require_string(message, "game_id")
        _validate_board(message["board"])
        if message["turn"] not in {"X", "O", None}:
            raise InvalidPayloadError("O campo 'turn' deve ser 'X', 'O' ou null")
        revision = _require_integer(message, "revision")
        if revision < 0:
            raise InvalidPayloadError("O campo 'revision' não pode ser negativo")
        return

    if message_type == "GAME_OVER":
        result = message.get("result")
        if result == "WIN":
            _require_exact_fields(message, {"game_id", "result", "winner"})
            _require_string(message, "game_id")
            _require_enum(message, "winner", _MARKS)
            return
        if result == "DRAW":
            _require_exact_fields(message, {"game_id", "result", "winner"})
            _require_string(message, "game_id")
            if message["winner"] is not None:
                raise InvalidPayloadError("GAME_OVER DRAW deve usar winner null")
            return
        if result == "ABORTED":
            _require_exact_fields(
                message, {"game_id", "result", "winner", "reason"}
            )
            _require_string(message, "game_id")
            if message["winner"] is not None:
                raise InvalidPayloadError("GAME_OVER ABORTED deve usar winner null")
            if _require_string(message, "reason") != "OPPONENT_LEFT":
                raise InvalidPayloadError(
                    "GAME_OVER ABORTED deve usar reason 'OPPONENT_LEFT'"
                )
            return
        raise InvalidPayloadError(
            "O campo 'result' deve ser 'WIN', 'DRAW' ou 'ABORTED'"
        )

    if message_type == "ERROR":
        _require_exact_fields(message, {"code", "message"})
        _require_enum(message, "code", ERROR_CODES)
        _require_string(message, "message")
        return

    raise AssertionError(f"Validador ausente para o tipo {message_type}")


def validate_client_message(message: dict[str, Any]) -> None:
    """Valida uma mensagem recebida do cliente pelo servidor."""

    validate_payload(message)
    if message["type"] not in CLIENT_TO_SERVER_TYPES:
        raise InvalidDirectionError(
            f"{message['type']} não é permitido de cliente para servidor"
        )


def validate_server_message(message: dict[str, Any]) -> None:
    """Valida uma mensagem recebida do servidor pelo cliente."""

    validate_payload(message)
    if message["type"] not in SERVER_TO_CLIENT_TYPES:
        raise InvalidDirectionError(
            f"{message['type']} não é permitido de servidor para cliente"
        )


def make_message(message_type: str, /, **payload: Any) -> dict[str, Any]:
    """Cria e valida uma mensagem TTTP/1 com o envelope canônico."""

    message = {"type": message_type, "version": PROTOCOL_VERSION, **payload}
    validate_payload(message)
    return message


def encode_message(message: dict[str, Any]) -> bytes:
    """Serializa um objeto TTTP/1 como JSON UTF-8 terminado por LF."""

    validate_payload(message)

    try:
        serialized = json.dumps(
            message,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise MessageEncodingError("O payload não é serializável como JSON") from exc

    encoded = serialized.encode("utf-8") + MESSAGE_DELIMITER
    if len(encoded) > MAX_MESSAGE_BYTES:
        raise MessageTooLargeError(
            f"Mensagem possui {len(encoded)} bytes; limite: {MAX_MESSAGE_BYTES}"
        )
    return encoded


def _reject_nonstandard_constant(value: str) -> None:
    raise ValueError(f"Constante JSON não permitida: {value}")


def _reject_duplicate_fields(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    message: dict[str, Any] = {}
    for key, value in pairs:
        if key in message:
            raise ValueError(f"Campo JSON duplicado: {key}")
        message[key] = value
    return message


def decode_message(data: bytes) -> dict[str, Any]:
    """Decodifica o conteúdo de um registro, sem o LF delimitador.

    ``MessageChannel`` é responsável por localizar e remover o delimitador.
    Esta função recebe exatamente um registro e rejeita LF literal.
    """

    if not isinstance(data, bytes):
        raise TypeError("data deve ser bytes")
    if MESSAGE_DELIMITER in data:
        raise MessageDecodingError("O registro não deve conter LF literal")
    if len(data) + len(MESSAGE_DELIMITER) > MAX_MESSAGE_BYTES:
        raise MessageTooLargeError(
            "O registro excede o limite após considerar o LF final"
        )

    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise MessageDecodingError("O registro não é UTF-8 válido") from exc

    try:
        message = json.loads(
            text,
            parse_constant=_reject_nonstandard_constant,
            object_pairs_hook=_reject_duplicate_fields,
        )
    except (json.JSONDecodeError, ValueError) as exc:
        raise MessageDecodingError("O registro não contém JSON válido") from exc

    if not isinstance(message, dict):
        raise MessageDecodingError("A raiz da mensagem deve ser um objeto JSON")

    validate_payload(message)
    return message


__all__ = [
    "CLIENT_TO_SERVER_TYPES",
    "ERROR_CODES",
    "InvalidDirectionError",
    "InvalidEnvelopeError",
    "InvalidPayloadError",
    "MAX_MESSAGE_BYTES",
    "MESSAGE_DELIMITER",
    "MESSAGE_TYPES",
    "MOVE_REJECTION_CODES",
    "MessageDecodingError",
    "MessageEncodingError",
    "MessageTooLargeError",
    "PROTOCOL_VERSION",
    "ProtocolError",
    "SERVER_TO_CLIENT_TYPES",
    "UnknownMessageTypeError",
    "UnsupportedVersionError",
    "decode_message",
    "encode_message",
    "make_message",
    "validate_client_message",
    "validate_envelope",
    "validate_payload",
    "validate_server_message",
]
