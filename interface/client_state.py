"""Modelo de apresentação testável usado pela GUI e pelo espelho do cliente."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from shared.protocol import validate_server_message


class ClientPhase(str, Enum):
    DISCONNECTED = "DESCONECTADO"
    CONNECTING = "CONECTANDO"
    HANDSHAKE = "IDENTIFICANDO"
    WAITING = "AGUARDANDO"
    IN_GAME = "EM_PARTIDA"
    ENDED = "ENCERRADO"


class ClientStateError(ValueError):
    """A sequência recebida não combina com o estado de apresentação."""


def _empty_board() -> list[list[str]]:
    return [["", "", ""] for _ in range(3)]


@dataclass
class ClientPresentationState:
    phase: ClientPhase = ClientPhase.DISCONNECTED
    client_id: str = "—"
    game_id: str = "—"
    mark: str = "—"
    board: list[list[str]] = field(default_factory=_empty_board)
    turn: str | None = None
    revision: int = -1
    pending_move: tuple[int, int] | None = None
    expected_revision: int | None = None
    notice: str = "Pronto para conectar."
    result: str | None = None

    def begin_connection(self) -> None:
        if self.phase is not ClientPhase.DISCONNECTED:
            raise ClientStateError("A conexão já foi iniciada")
        self.phase = ClientPhase.CONNECTING
        self.notice = "Abrindo socket TCP..."

    def connection_established(self) -> None:
        if self.phase is not ClientPhase.CONNECTING:
            raise ClientStateError("Conexão TCP fora da fase esperada")
        self.phase = ClientPhase.HANDSHAKE
        self.notice = "TCP conectado; enviando HELLO."

    def reset(self, notice: str = "Conexão encerrada.") -> None:
        self.phase = ClientPhase.DISCONNECTED
        self.client_id = "—"
        self.game_id = "—"
        self.mark = "—"
        self.board = _empty_board()
        self.turn = None
        self.revision = -1
        self.pending_move = None
        self.expected_revision = None
        self.result = None
        self.notice = notice

    def prepare_rejoin(self) -> None:
        if self.phase is not ClientPhase.ENDED:
            raise ClientStateError("Nova partida só pode ser solicitada após GAME_OVER")
        self.phase = ClientPhase.WAITING
        self.pending_move = None
        self.expected_revision = None
        self.result = None
        self.notice = "JOIN enviado; aguardando novo pareamento."

    def mark_move_sent(self, row: int, col: int) -> None:
        if not self.can_play(row, col):
            raise ClientStateError("A jogada não está disponível neste estado")
        self.pending_move = (row, col)
        self.notice = f"MOVE ({row},{col}) enviado; aguardando confirmação."

    def can_play(self, row: int, col: int) -> bool:
        return (
            self.phase is ClientPhase.IN_GAME
            and self.turn == self.mark
            and self.pending_move is None
            and type(row) is int
            and type(col) is int
            and row in range(3)
            and col in range(3)
            and self.board[row][col] == ""
        )

    def apply_server_message(self, message: dict[str, Any]) -> str:
        """Aplica somente estado confirmado pelo servidor e devolve uma descrição."""

        validate_server_message(message)
        kind = message["type"]

        if kind == "WELCOME":
            if self.phase is not ClientPhase.HANDSHAKE:
                raise ClientStateError("WELCOME fora do handshake")
            self.client_id = message["client_id"]
            self.phase = ClientPhase.WAITING
            self.notice = "Identificado; JOIN será enviado ao lobby."
            return "WELCOME validado; sessão identificada."

        if kind == "WAITING":
            if self.phase not in {ClientPhase.WAITING, ClientPhase.ENDED}:
                raise ClientStateError("WAITING fora do lobby")
            self.phase = ClientPhase.WAITING
            self.notice = "No lobby; aguardando outro jogador."
            return "WAITING apresentado sem bloquear a recepção da rede."

        if kind == "START":
            if self.phase not in {ClientPhase.WAITING, ClientPhase.ENDED}:
                raise ClientStateError("START fora do pareamento")
            if message["first_turn"] != "X":
                raise ClientStateError("START não define X como primeiro turno")
            self.game_id = message["game_id"]
            self.mark = message["mark"]
            self.board = _empty_board()
            self.turn = message["first_turn"]
            self.revision = -1
            self.pending_move = None
            self.expected_revision = None
            self.result = None
            self.phase = ClientPhase.IN_GAME
            self.notice = f"Partida {self.game_id} iniciada; você é {self.mark}."
            return "START armazenado; marca e game_id vieram do servidor."

        if kind == "BOARD":
            self._require_current_game(message)
            revision = message["revision"]
            if self.revision == -1:
                if revision != 0:
                    raise ClientStateError("O primeiro BOARD deve ter revision 0")
            elif revision != self.revision + 1:
                raise ClientStateError("BOARD não avança exatamente uma revisão")
            if self.expected_revision is not None and revision != self.expected_revision:
                raise ClientStateError("BOARD não corresponde ao MOVE_RESULT aceito")
            self.board = [list(row) for row in message["board"]]
            self.turn = message["turn"]
            self.revision = revision
            self.pending_move = None
            self.expected_revision = None
            self.notice = (
                "Aguardando GAME_OVER oficial."
                if self.turn is None
                else ("Sua vez de jogar." if self.turn == self.mark else "Vez do adversário.")
            )
            return "BOARD oficial aplicado à apresentação; nenhuma jogada foi antecipada."

        if kind == "MOVE_RESULT":
            self._require_current_game(message)
            if message["status"] == "REJECTED":
                self.pending_move = None
                self.expected_revision = None
                self.notice = f"Jogada recusada: {message['message']}"
                return f"MOVE rejeitado sem alterar o tabuleiro ({message['code']})."
            if self.pending_move is not None and self.pending_move != (message["row"], message["col"]):
                raise ClientStateError("MOVE_RESULT não corresponde à posição solicitada")
            if message["revision"] != self.revision + 1:
                raise ClientStateError("MOVE_RESULT possui revisão inesperada")
            self.expected_revision = message["revision"]
            self.notice = "Jogada aceita; aguardando BOARD oficial."
            return "MOVE_RESULT aceito; apresentação ainda aguarda BOARD."

        if kind == "GAME_OVER":
            self._require_current_game(message)
            self.phase = ClientPhase.ENDED
            self.turn = None
            self.pending_move = None
            self.expected_revision = None
            self.result = message["result"]
            if message["result"] == "WIN":
                self.notice = f"Fim de jogo: {message['winner']} venceu."
            elif message["result"] == "DRAW":
                self.notice = "Fim de jogo: empate."
            else:
                self.notice = "Partida interrompida: o adversário saiu."
            return "GAME_OVER oficial encerrou o diálogo da partida."

        if kind == "ERROR":
            self.notice = f"Erro {message['code']}: {message['message']}"
            return "ERROR apresentado com código e orientação do servidor."

        if kind in {"PING", "PONG"}:
            return f"{kind} consumido sem alterar o jogo."

        raise ClientStateError(f"Mensagem não tratada pela apresentação: {kind}")

    def _require_current_game(self, message: dict[str, Any]) -> None:
        if self.game_id == "—" or message.get("game_id") != self.game_id:
            raise ClientStateError("Mensagem pertence a outra partida")


__all__ = ["ClientPhase", "ClientPresentationState", "ClientStateError"]
