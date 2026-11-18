"""Transporte TCP compartilhado para mensagens TTTP/1."""

from __future__ import annotations

import socket
import threading
import weakref
from collections.abc import Mapping
from typing import Any, TypeAlias

from shared.protocol import (
    MAX_MESSAGE_BYTES,
    MESSAGE_DELIMITER,
    MessageTooLargeError,
    decode_message,
    encode_message,
    make_message,
    validate_payload,
)
from shared.telemetry import TraceObserver, emit_trace, trace_event

DEFAULT_RECV_SIZE = MAX_MESSAGE_BYTES


class TransportError(ConnectionError):
    """Erro base de conexão ou operação de socket."""


class ConnectionClosedError(TransportError):
    """A conexão foi fechada localmente ou chegou ao EOF."""


class TransportTimeoutError(TransportError):
    """Uma operação de socket excedeu o timeout configurado."""


class SocketOperationError(TransportError):
    """O sistema operacional rejeitou uma operação de socket."""


class MessageChannel:
    """Canal JSONL com buffer e locks persistentes por conexão."""

    def __init__(
        self,
        connection: socket.socket,
        *,
        recv_size: int = DEFAULT_RECV_SIZE,
        trace_observer: TraceObserver | None = None,
        trace_actor: str = "Canal TCP",
        trace_peer: str = "",
    ):
        if recv_size <= 0:
            raise ValueError("recv_size deve ser positivo")

        self._socket = connection
        self._recv_size = recv_size
        self._buffer = bytearray()
        self._send_lock = threading.Lock()
        self._receive_lock = threading.Lock()
        self._state_lock = threading.Lock()
        self._closed = False
        self._trace_observer = trace_observer
        self._trace_actor = trace_actor
        self._trace_peer = trace_peer

    @property
    def socket(self) -> socket.socket:
        return self._socket

    @property
    def closed(self) -> bool:
        with self._state_lock:
            return self._closed

    @property
    def buffered_bytes(self) -> int:
        """Quantidade de bytes residuais ainda não consumidos."""

        with self._receive_lock:
            return len(self._buffer)

    def _ensure_open(self) -> None:
        with self._state_lock:
            if self._closed:
                raise ConnectionClosedError("A conexão já está fechada")

    def configure_tracing(
        self,
        observer: TraceObserver | None,
        *,
        actor: str | None = None,
        peer: str | None = None,
    ) -> None:
        """Configura a explicação local do canal sem alterar bytes na rede."""

        with self._state_lock:
            self._trace_observer = observer
            if actor is not None:
                self._trace_actor = actor
            if peer is not None:
                self._trace_peer = peer

    def _trace(
        self,
        direction: str,
        action: str,
        payload: Mapping[str, Any] | None = None,
        *,
        detail: str = "",
        byte_count: int | None = None,
        buffered_bytes: int | None = None,
    ) -> None:
        with self._state_lock:
            observer = self._trace_observer
            actor = self._trace_actor
            peer = self._trace_peer
        message_type = None if payload is None else str(payload.get("type", ""))
        emit_trace(
            observer,
            trace_event(
                layer="TRANSPORTE",
                direction=direction,  # type: ignore[arg-type]
                action=action,
                actor=actor,
                peer=peer,
                message_type=message_type or None,
                payload=payload,
                detail=detail,
                byte_count=byte_count,
                buffered_bytes=buffered_bytes,
            ),
        )

    def send_message(self, payload: Mapping[str, Any]) -> None:
        """Codifica e envia um registro completo sem intercalar threads."""

        data = encode_message(dict(payload))
        failure: tuple[TransportError, BaseException] | None = None

        with self._send_lock:
            self._ensure_open()
            try:
                self._socket.sendall(data)
            except socket.timeout as exc:
                failure = (TransportTimeoutError("Timeout durante o envio"), exc)
            except OSError as exc:
                failure = (SocketOperationError("Falha ao enviar pelo socket"), exc)

        if failure is not None:
            self.close()
            raise failure[0] from failure[1]
        self._trace(
            "SAIDA",
            "encode_message + sendall",
            payload,
            detail="JSON → UTF-8 → LF; registro enviado integralmente pelo socket TCP.",
            byte_count=len(data),
        )

    def receive_message(self) -> dict[str, Any]:
        """Recebe exatamente uma mensagem, preservando bytes posteriores."""

        with self._receive_lock:
            self._ensure_open()

            while True:
                delimiter_index = self._buffer.find(MESSAGE_DELIMITER)
                if delimiter_index >= 0:
                    record_size = delimiter_index + len(MESSAGE_DELIMITER)
                    if record_size > MAX_MESSAGE_BYTES:
                        raise MessageTooLargeError(
                            f"Registro possui {record_size} bytes; "
                            f"limite: {MAX_MESSAGE_BYTES}"
                        )

                    record = bytes(self._buffer[:delimiter_index])
                    del self._buffer[:record_size]
                    message = decode_message(record)
                    self._trace(
                        "ENTRADA",
                        "recv + buffer + decode_message",
                        message,
                        detail=(
                            "LF delimitou um registro; bytes posteriores permaneceram "
                            "no buffer da conexão."
                        ),
                        byte_count=record_size,
                        buffered_bytes=len(self._buffer),
                    )
                    return message

                if len(self._buffer) >= MAX_MESSAGE_BYTES:
                    raise MessageTooLargeError(
                        "Buffer atingiu o limite sem encontrar LF"
                    )

                remaining_capacity = MAX_MESSAGE_BYTES - len(self._buffer)
                try:
                    chunk = self._socket.recv(
                        min(self._recv_size, remaining_capacity)
                    )
                except socket.timeout as exc:
                    raise TransportTimeoutError("Timeout durante a recepção") from exc
                except OSError as exc:
                    self.close()
                    raise SocketOperationError("Falha ao receber pelo socket") from exc

                if chunk == b"":
                    self.close()
                    raise ConnectionClosedError("Fim do fluxo TCP (EOF)")

                self._buffer.extend(chunk)

    def close(self) -> None:
        """Fecha o socket de modo idempotente."""

        with self._send_lock:
            with self._state_lock:
                if self._closed:
                    return
                self._closed = True

            try:
                self._socket.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                self._socket.close()
            except OSError:
                pass

    def set_timeout(self, timeout: float | None) -> None:
        """Configura timeout local sem impor uma política ao jogo.

        ``None`` restaura o modo bloqueante. Valores positivos configuram o
        timeout de operações futuras. Timeout não encerra automaticamente uma
        recepção, pois o buffer parcial pode ser retomado.
        """

        if timeout is not None and timeout <= 0:
            raise ValueError("timeout deve ser positivo ou None")
        self._ensure_open()
        try:
            self._socket.settimeout(timeout)
        except OSError as exc:
            self.close()
            raise SocketOperationError("Falha ao configurar timeout") from exc

    def get_timeout(self) -> float | None:
        """Retorna o timeout configurado no socket."""

        self._ensure_open()
        try:
            return self._socket.gettimeout()
        except OSError as exc:
            self.close()
            raise SocketOperationError("Falha ao consultar timeout") from exc

    def __enter__(self) -> MessageChannel:
        self._ensure_open()
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()


ConnectionLike: TypeAlias = MessageChannel | socket.socket

_channel_registry: weakref.WeakKeyDictionary[socket.socket, MessageChannel] = (
    weakref.WeakKeyDictionary()
)
_channel_registry_lock = threading.Lock()


def _as_channel(connection: ConnectionLike) -> MessageChannel:
    if isinstance(connection, MessageChannel):
        return connection

    with _channel_registry_lock:
        channel = _channel_registry.get(connection)
        if channel is None:
            channel = MessageChannel(connection)
            _channel_registry[connection] = channel
        return channel


def connect_to_server(
    host: str,
    port: int,
    *,
    timeout: float | None = None,
    trace_observer: TraceObserver | None = None,
    trace_actor: str = "Cliente / transporte",
    trace_peer: str | None = None,
) -> MessageChannel:
    """Abre uma conexão TCP cliente e devolve um canal TTTP/1.

    ``timeout`` limita somente a tentativa de conexão. Depois de conectado, o
    socket volta ao modo bloqueante para não impor timeout curto às jogadas.
    """

    connection: socket.socket | None = None
    try:
        connection = socket.create_connection((host, port), timeout=timeout)
        connection.settimeout(None)
    except socket.timeout as exc:
        if connection is not None:
            connection.close()
        raise TransportTimeoutError("Timeout ao conectar ao servidor") from exc
    except OSError as exc:
        if connection is not None:
            connection.close()
        raise SocketOperationError("Não foi possível conectar ao servidor") from exc

    peer = trace_peer or f"{host}:{port}"
    channel = MessageChannel(
        connection,
        trace_observer=trace_observer,
        trace_actor=trace_actor,
        trace_peer=peer,
    )
    emit_trace(
        trace_observer,
        trace_event(
            layer="TRANSPORTE",
            direction="INTERNO",
            action="socket.create_connection",
            actor=trace_actor,
            peer=peer,
            detail="Conexão TCP estabelecida; o canal volta ao modo bloqueante.",
        ),
    )
    return channel


def create_listening_socket(
    host: str,
    port: int,
    *,
    backlog: int = socket.SOMAXCONN,
    reuse_address: bool = True,
) -> socket.socket:
    """Cria, associa e coloca um socket TCP no modo de escuta."""

    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        if reuse_address:
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind((host, port))
        listener.listen(backlog)
    except OSError as exc:
        listener.close()
        raise SocketOperationError("Não foi possível iniciar a escuta TCP") from exc
    return listener


def accept_connection(listener: socket.socket) -> tuple[MessageChannel, Any]:
    """Aceita uma conexão já enfileirada no listener.

    A decisão de quando e em qual laço chamar esta função pertence ao servidor.
    """

    try:
        connection, address = listener.accept()
    except socket.timeout as exc:
        raise TransportTimeoutError("Timeout ao aceitar conexão") from exc
    except OSError as exc:
        raise SocketOperationError("Falha ao aceitar conexão") from exc
    return MessageChannel(connection), address


def send_message(connection: ConnectionLike, payload: Mapping[str, Any]) -> None:
    """Wrapper que reutiliza o mesmo canal para um socket bruto."""

    _as_channel(connection).send_message(payload)


def receive_message(connection: ConnectionLike) -> dict[str, Any]:
    """Wrapper que preserva o buffer residual entre chamadas."""

    return _as_channel(connection).receive_message()


def close_connection(connection: ConnectionLike) -> None:
    """Fecha um canal ou socket bruto de modo idempotente."""

    if isinstance(connection, MessageChannel):
        connection.close()
        return

    with _channel_registry_lock:
        channel = _channel_registry.get(connection)
    if channel is None:
        channel = MessageChannel(connection)
    channel.close()


def send_ping(connection: ConnectionLike) -> None:
    """Envia a sondagem opcional PING sem alterar estados do jogo."""

    send_message(connection, make_message("PING"))


def handle_heartbeat_message(
    connection: ConnectionLike, message: Mapping[str, Any]
) -> bool:
    """Processa PING/PONG e informa se a mensagem foi consumida.

    `PING` recebe uma resposta `PONG`. `PONG` apenas confirma atividade. Outros
    tipos retornam ``False`` e devem seguir para o roteamento normal da
    aplicação.
    """

    normalized = dict(message)
    validate_payload(normalized)
    if normalized["type"] == "PING":
        send_message(connection, make_message("PONG"))
        return True
    if normalized["type"] == "PONG":
        return True
    return False


__all__ = [
    "ConnectionClosedError",
    "DEFAULT_RECV_SIZE",
    "MessageChannel",
    "SocketOperationError",
    "TransportError",
    "TransportTimeoutError",
    "TraceObserver",
    "accept_connection",
    "close_connection",
    "connect_to_server",
    "create_listening_socket",
    "handle_heartbeat_message",
    "receive_message",
    "send_message",
    "send_ping",
]
