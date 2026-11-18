"""Servidor TCP do Jogo da Velha (TTTP/1).

Uma thread de leitura e uma thread de escrita por conexão. Toda mensagem
destinada a um cliente passa por uma fila de saída própria, enfileirada sob o
lock da partida: assim a ordem lógica (``MOVE_RESULT``, ``BOARD``,
``GAME_OVER``) é preservada mesmo com jogadas concorrentes, e nenhuma operação
de rede bloqueante ocorre com o lock da partida retido.
"""

from __future__ import annotations

import argparse
import itertools
import logging
import queue
import socket
import sys
import threading
from enum import Enum
from typing import Any

from server.game import Game
from server.lobby import Lobby
from shared.protocol import (
    MessageTooLargeError,
    ProtocolError,
    UnknownMessageTypeError,
    UnsupportedVersionError,
    make_message,
    validate_client_message,
)
from shared.transport import (
    ConnectionClosedError,
    MessageChannel,
    TransportError,
    TransportTimeoutError,
    accept_connection,
    create_listening_socket,
)
from shared.telemetry import TraceObserver, emit_trace, trace_event

LOGGER = logging.getLogger("tttp.server")

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 5000
DEFAULT_HANDSHAKE_TIMEOUT = 30.0
_ACCEPT_POLL_SECONDS = 0.2

_CLOSE = object()


class SessionState(str, Enum):
    CONNECTED = "CONECTADO"
    IDENTIFIED = "IDENTIFICADO"
    WAITING = "AGUARDANDO"
    IN_GAME = "EM_PARTIDA"
    ENDED = "ENCERRADO"


class Session:
    """Uma conexão de cliente: estado de sessão, fila de saída e partida atual."""

    def __init__(
        self,
        client_id: str,
        channel: MessageChannel,
        address: Any,
        trace_observer: TraceObserver | None = None,
    ) -> None:
        self.client_id = client_id
        self.channel = channel
        self.address = address
        self.state = SessionState.CONNECTED
        self.game: Game | None = None
        self._outbox: queue.Queue[Any] = queue.Queue()
        self._flag_lock = threading.Lock()
        self._disconnected = False
        self._trace_observer = trace_observer
        self.channel.configure_tracing(
            trace_observer,
            actor="Servidor / transporte",
            peer=f"{client_id} {address}",
        )

    def is_connected(self) -> bool:
        with self._flag_lock:
            return not self._disconnected

    def mark_disconnected(self) -> bool:
        """``True`` somente na primeira chamada (limpeza executada uma vez)."""

        with self._flag_lock:
            if self._disconnected:
                return False
            self._disconnected = True
            return True

    def send(self, message: dict[str, Any]) -> None:
        """Enfileira sem bloquear; descarta se a sessão já foi encerrada."""

        if self.is_connected():
            emit_trace(
                self._trace_observer,
                trace_event(
                    layer="APLICACAO",
                    direction="SAIDA",
                    action="Resposta enfileirada pela aplicação",
                    actor="Servidor / aplicação",
                    peer=self.client_id,
                    message_type=message["type"],
                    payload=message,
                    detail=(
                        "A fila preserva a ordem lógica; a thread de escrita "
                        "acionará shared.transport sem reter o lock da partida."
                    ),
                ),
            )
            self._outbox.put(message)

    def close_after_flush(self) -> None:
        """Fecha o canal depois de enviar o que já está na fila."""

        self._outbox.put(_CLOSE)

    def writer_loop(self) -> None:
        while True:
            item = self._outbox.get()
            if item is _CLOSE:
                break
            try:
                self.channel.send_message(item)
            except TransportError as exc:
                # Socket já fechado/quebrado: tratado localmente, sem afetar a partida.
                LOGGER.info("%s: falha ao enviar %s: %s", self.client_id, item.get("type"), exc)
                break
        self.channel.close()


class GameServer:
    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        *,
        handshake_timeout: float | None = DEFAULT_HANDSHAKE_TIMEOUT,
        trace_observer: TraceObserver | None = None,
    ) -> None:
        self._host = host
        self._port = port
        self._handshake_timeout = handshake_timeout
        self._lobby = Lobby()
        self._sessions: dict[str, Session] = {}
        self._sessions_lock = threading.Lock()
        self._matchmaking_lock = threading.Lock()
        self._client_counter = itertools.count(1)
        self._listener: socket.socket | None = None
        self._accept_thread: threading.Thread | None = None
        self._stopping = threading.Event()
        self._trace_observer = trace_observer

    # ------------------------------------------------------------------ ciclo de vida

    @property
    def address(self) -> tuple[str, int]:
        if self._listener is None:
            raise RuntimeError("Servidor não iniciado")
        host, port = self._listener.getsockname()[:2]
        return host, port

    def status_snapshot(self) -> dict[str, Any]:
        """Fotografia somente de leitura para a interface do operador."""

        with self._sessions_lock:
            sessions = list(self._sessions.values())
        rows = [
            {
                "client_id": session.client_id,
                "address": str(session.address),
                "state": session.state.value,
                "game_id": session.game.game_id if session.game is not None else "—",
                "connected": session.is_connected(),
            }
            for session in sessions
        ]
        unique_games = {
            session.game.game_id: session.game
            for session in sessions
            if session.game is not None and session.is_connected()
        }
        game_rows = []
        for game in unique_games.values():
            snapshot = game.snapshot()
            game_rows.append(
                {
                    "game_id": snapshot.game_id,
                    "revision": snapshot.revision,
                    "turn": snapshot.turn,
                    "status": game.status.value,
                }
            )
        try:
            address: tuple[str, int] | None = self.address
        except RuntimeError:
            address = None
        return {
            "running": self._listener is not None and not self._stopping.is_set(),
            "address": address,
            "sessions": rows,
            "games": sorted(game_rows, key=lambda row: row["game_id"]),
            "session_count": sum(1 for row in rows if row["connected"]),
            "waiting_count": self._lobby.waiting_count(),
            "game_count": len(unique_games),
        }

    def _trace(
        self,
        direction: str,
        action: str,
        *,
        session: Session | None = None,
        message: dict[str, Any] | None = None,
        detail: str = "",
    ) -> None:
        emit_trace(
            self._trace_observer,
            trace_event(
                layer="APLICACAO",
                direction=direction,  # type: ignore[arg-type]
                action=action,
                actor="Servidor / aplicação",
                peer="" if session is None else session.client_id,
                message_type=None if message is None else message.get("type"),
                payload=message,
                detail=detail,
            ),
        )

    def start(self) -> tuple[str, int]:
        """Abre a escuta e atende conexões em segundo plano."""

        self._listener = create_listening_socket(self._host, self._port)
        self._listener.settimeout(_ACCEPT_POLL_SECONDS)
        self._stopping.clear()
        self._accept_thread = threading.Thread(
            target=self._accept_loop, name="tttp-accept", daemon=True
        )
        self._accept_thread.start()
        LOGGER.info("Servidor escutando em %s:%s", *self.address)
        self._trace(
            "INTERNO",
            "Servidor em escuta",
            detail=f"A aplicação solicitou listen/accept em {self.address[0]}:{self.address[1]}.",
        )
        return self.address

    def serve_forever(self) -> None:
        self.start()
        try:
            while not self._stopping.wait(0.5):
                pass
        except KeyboardInterrupt:
            LOGGER.info("Interrompido pelo operador")
        finally:
            self.stop()

    def stop(self) -> None:
        self._stopping.set()
        if self._accept_thread is not None:
            self._accept_thread.join(timeout=2)
            self._accept_thread = None
        if self._listener is not None:
            try:
                self._listener.close()
            except OSError:
                pass
            self._listener = None
        with self._sessions_lock:
            sessions = list(self._sessions.values())
        for session in sessions:
            session.channel.close()
        LOGGER.info("Servidor encerrado")
        self._trace("INTERNO", "Servidor encerrado", detail="Listener e canais TCP foram fechados.")

    # ------------------------------------------------------------------ aceitação

    def _accept_loop(self) -> None:
        listener = self._listener
        assert listener is not None
        while not self._stopping.is_set():
            try:
                channel, address = accept_connection(listener)
            except TransportTimeoutError:
                continue
            except TransportError as exc:
                if not self._stopping.is_set():
                    LOGGER.error("Falha ao aceitar conexão: %s", exc)
                return
            client_id = f"c{next(self._client_counter)}"
            session = Session(
                client_id,
                channel,
                address,
                trace_observer=self._trace_observer,
            )
            with self._sessions_lock:
                self._sessions[client_id] = session
            LOGGER.info("%s: conexão aceita de %s", client_id, address)
            self._trace(
                "INTERNO",
                "Conexão aceita",
                session=session,
                detail="accept() criou um canal; a sessão ainda aguarda HELLO.",
            )
            threading.Thread(
                target=session.writer_loop, name=f"{client_id}-writer", daemon=True
            ).start()
            threading.Thread(
                target=self._serve_session,
                args=(session,),
                name=f"{client_id}-reader",
                daemon=True,
            ).start()

    # ------------------------------------------------------------------ sessão

    def _serve_session(self, session: Session) -> None:
        try:
            if self._handshake_timeout is not None:
                session.channel.set_timeout(self._handshake_timeout)
            while self._handle_next(session):
                pass
        except TransportError as exc:
            LOGGER.info("%s: conexão encerrada (%s)", session.client_id, exc)
        except Exception:  # noqa: BLE001 - nunca derrubar o servidor por uma sessão
            LOGGER.exception("%s: erro inesperado na sessão", session.client_id)
        finally:
            self._disconnect(session)

    def _handle_next(self, session: Session) -> bool:
        """Lê e processa uma mensagem; ``False`` encerra a sessão."""

        try:
            message = session.channel.receive_message()
        except TransportTimeoutError:
            if session.state is SessionState.CONNECTED:
                LOGGER.info("%s: timeout de handshake", session.client_id)
                return False
            return True
        except ConnectionClosedError:
            return False
        except UnsupportedVersionError:
            return self._fatal(session, "UNSUPPORTED_VERSION", "Versão do protocolo não suportada")
        except MessageTooLargeError:
            return self._fatal(session, "MESSAGE_TOO_LARGE", "Mensagem excede o limite de 4096 bytes")
        except UnknownMessageTypeError:
            self._error(session, "UNKNOWN_TYPE", "Tipo de mensagem desconhecido")
            return True
        except ProtocolError as exc:
            LOGGER.info("%s: mensagem inválida: %s", session.client_id, exc)
            self._error(session, "BAD_FORMAT", "Mensagem inválida")
            return True

        try:
            validate_client_message(message)
        except ProtocolError as exc:
            LOGGER.info("%s: direção inválida: %s", session.client_id, exc)
            self._error(session, "BAD_FORMAT", "Mensagem inválida")
            return True

        self._trace(
            "ENTRADA",
            "Mensagem entregue à aplicação",
            session=session,
            message=message,
            detail="shared.transport reconstruiu o registro JSONL antes do roteamento.",
        )
        return self._dispatch(session, message)

    def _dispatch(self, session: Session, message: dict[str, Any]) -> bool:
        kind = message["type"]
        if kind == "QUIT":
            LOGGER.info("%s: QUIT", session.client_id)
            return False
        if kind == "PING":
            session.send(make_message("PONG"))
            return True
        if kind == "PONG":
            return True
        if kind == "HELLO":
            return self._on_hello(session)
        if kind == "JOIN":
            return self._on_join(session)
        if kind == "MOVE":
            return self._on_move(session, message)
        self._error(session, "UNKNOWN_TYPE", "Tipo de mensagem desconhecido")
        return True

    def _on_hello(self, session: Session) -> bool:
        if session.state is not SessionState.CONNECTED:
            self._error(session, "INVALID_STATE", "HELLO fora da fase permitida")
            return True
        session.state = SessionState.IDENTIFIED
        session.channel.set_timeout(None)  # sem timeout curto para o tempo de jogo
        self._trace(
            "INTERNO",
            "Handshake validado",
            session=session,
            detail="HELLO válido promoveu a sessão para IDENTIFICADO.",
        )
        session.send(make_message("WELCOME", client_id=session.client_id))
        return True

    def _on_join(self, session: Session) -> bool:
        if session.state not in (SessionState.IDENTIFIED, SessionState.ENDED):
            self._error(session, "INVALID_STATE", "JOIN fora da fase permitida")
            return True
        with self._matchmaking_lock:
            session.game = None
            session.state = SessionState.WAITING
            game = self._lobby.join(session)
            if game is None:
                LOGGER.info("%s: aguardando adversário", session.client_id)
                self._trace(
                    "INTERNO",
                    "Sessão entrou no lobby",
                    session=session,
                    detail="JOIN válido; pareamento FIFO ainda não encontrou adversário.",
                )
                session.send(make_message("WAITING"))
            else:
                self._start_game(game)
        return True

    def _start_game(self, game: Game) -> None:
        with self._sessions_lock:
            sessions = {
                mark: self._sessions.get(client_id)
                for mark, client_id in game.players.items()
            }
        with game.lock:
            snapshot = game.snapshot()
            for mark, member in sessions.items():
                if member is None:
                    continue
                member.game = game
                member.state = SessionState.IN_GAME
                member.send(
                    make_message("START", game_id=game.game_id, mark=mark, first_turn="X")
                )
            for member in sessions.values():
                if member is not None:
                    member.send(self._board_message(snapshot))
            LOGGER.info("Partida %s iniciada: %s", game.game_id, game.players)
            self._trace(
                "INTERNO",
                "Partida criada",
                detail=(
                    f"{game.game_id}: servidor atribuiu X/O, turno X e BOARD revision 0."
                ),
            )
            # Um participante pode ter caído entre o pareamento e esta atribuição.
            if any(m is None or not m.is_connected() for m in sessions.values()):
                self._abort_game(game)

    def _on_move(self, session: Session, message: dict[str, Any]) -> bool:
        game = session.game
        if game is None or session.state not in (SessionState.IN_GAME, SessionState.ENDED):
            self._reject(session, message["game_id"], "NOT_IN_GAME", "Você não está em uma partida")
            return True

        with game.lock:
            outcome = game.play(session.client_id, message["game_id"], message["row"], message["col"])
            if not outcome.accepted:
                LOGGER.info(
                    "%s: MOVE rejeitado (%s) em %s", session.client_id, outcome.code, game.game_id
                )
                self._trace(
                    "INTERNO",
                    "Jogada rejeitada sem mutação",
                    session=session,
                    message=message,
                    detail=f"{outcome.code}: turno, tabuleiro e revision foram preservados.",
                )
                self._reject(session, message["game_id"], outcome.code, outcome.message)
                return True

            snapshot = outcome.snapshot
            LOGGER.info(
                "%s: MOVE aceito (%s,%s) em %s rev=%s",
                session.client_id, outcome.row, outcome.col, game.game_id, snapshot.revision,
            )
            self._trace(
                "INTERNO",
                "Jogada validada e aplicada",
                session=session,
                message=message,
                detail=(
                    f"Estado autoritativo avançou atomicamente para revision {snapshot.revision}."
                ),
            )
            session.send(
                make_message(
                    "MOVE_RESULT",
                    game_id=game.game_id,
                    status="ACCEPTED",
                    row=outcome.row,
                    col=outcome.col,
                    revision=snapshot.revision,
                )
            )
            members = self._members(game)
            for member in members:
                member.send(self._board_message(snapshot))
            if outcome.finished:
                LOGGER.info("Partida %s encerrada: %s %s", game.game_id, outcome.result, outcome.winner)
                self._trace(
                    "INTERNO",
                    "Resultado oficial calculado",
                    detail=f"{game.game_id}: {outcome.result}; winner={outcome.winner}.",
                )
                for member in members:
                    member.send(
                        make_message(
                            "GAME_OVER",
                            game_id=game.game_id,
                            result=outcome.result,
                            winner=outcome.winner,
                        )
                    )
                    member.state = SessionState.ENDED
        return True

    # ------------------------------------------------------------------ utilitários

    def _members(self, game: Game) -> list[Session]:
        with self._sessions_lock:
            found = [self._sessions.get(cid) for cid in game.players.values()]
        return [s for s in found if s is not None]

    @staticmethod
    def _board_message(snapshot: Any) -> dict[str, Any]:
        return make_message(
            "BOARD",
            game_id=snapshot.game_id,
            board=snapshot.board_as_lists(),
            turn=snapshot.turn,
            revision=snapshot.revision,
        )

    def _reject(self, session: Session, game_id: str, code: str, text: str) -> None:
        session.send(
            make_message(
                "MOVE_RESULT", game_id=game_id, status="REJECTED", code=code, message=text
            )
        )

    def _error(self, session: Session, code: str, text: str) -> None:
        session.send(make_message("ERROR", code=code, message=text))

    def _fatal(self, session: Session, code: str, text: str) -> bool:
        self._error(session, code, text)
        return False

    def _abort_game(self, game: Game) -> None:
        """Aborta a partida e avisa os participantes ainda conectados."""

        with game.lock:
            if not game.abort():
                return
            LOGGER.info("Partida %s abortada", game.game_id)
            self._trace(
                "INTERNO",
                "Partida abortada",
                detail=f"{game.game_id}: desconexão; abandono não foi convertido em vitória.",
            )
            for member in self._members(game):
                if member.is_connected():
                    member.send(
                        make_message(
                            "GAME_OVER",
                            game_id=game.game_id,
                            result="ABORTED",
                            winner=None,
                            reason="OPPONENT_LEFT",
                        )
                    )
                    member.state = SessionState.ENDED

    def _disconnect(self, session: Session) -> None:
        if not session.mark_disconnected():
            return
        LOGGER.info("%s: sessão encerrada (estado %s)", session.client_id, session.state.value)
        self._lobby.remove(session)
        game = session.game
        if game is not None:
            self._abort_game(game)
        with self._sessions_lock:
            self._sessions.pop(session.client_id, None)
        session.close_after_flush()


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Servidor do Jogo da Velha (TTTP/1)")
    parser.add_argument("--host", default=DEFAULT_HOST, help="endereço de escuta (padrão: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="porta TCP (padrão: 5000)")
    parser.add_argument(
        "--handshake-timeout",
        type=float,
        default=DEFAULT_HANDSHAKE_TIMEOUT,
        help="segundos para o cliente enviar HELLO (padrão: 30)",
    )
    parser.add_argument("--log-level", default="INFO", help="DEBUG, INFO, WARNING...")
    display = parser.add_mutually_exclusive_group()
    display.add_argument(
        "--gui",
        action="store_true",
        help="força a interface gráfica mesmo sem terminal interativo",
    )
    display.add_argument(
        "--terminal-only",
        action="store_true",
        help="mantém somente o servidor textual legado",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_arg_parser().parse_args(argv)
    logging.basicConfig(
        level=args.log_level.upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    use_gui = args.gui or (
        not args.terminal_only and sys.stdin.isatty() and sys.stdout.isatty()
    )
    if use_gui:
        from interface.server_window import run_server_app

        run_server_app(
            args.host,
            args.port,
            handshake_timeout=args.handshake_timeout,
        )
        return
    GameServer(args.host, args.port, handshake_timeout=args.handshake_timeout).serve_forever()


if __name__ == "__main__":
    main()
