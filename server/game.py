"""Estado autoritativo e regras puras do Jogo da Velha 3x3.

Este módulo não conhece sockets nem mensagens TTTP/1: recebe dados já
validados sintaticamente e devolve resultados que o servidor converte em
mensagens. Toda alteração de estado passa por ``Game.play`` ou ``Game.abort``,
que são atômicos por partida.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from enum import Enum

BOARD_SIZE = 3
MARKS = ("X", "O")
EMPTY = ""

Board = tuple[tuple[str, ...], ...]

_LINES: tuple[tuple[tuple[int, int], ...], ...] = (
    *(tuple((row, col) for col in range(BOARD_SIZE)) for row in range(BOARD_SIZE)),
    *(tuple((row, col) for row in range(BOARD_SIZE)) for col in range(BOARD_SIZE)),
    tuple((i, i) for i in range(BOARD_SIZE)),
    tuple((i, BOARD_SIZE - 1 - i) for i in range(BOARD_SIZE)),
)


class GameStatus(str, Enum):
    """Estado interno da partida, distinto do estado da sessão TCP."""

    ACTIVE = "ATIVA"
    FINISHED = "FINALIZADA"
    ABORTED = "ABORTADA"


def empty_board() -> Board:
    return tuple(tuple(EMPTY for _ in range(BOARD_SIZE)) for _ in range(BOARD_SIZE))


def find_winner(board: Board) -> str | None:
    """Confere as 3 linhas, 3 colunas e 2 diagonais."""

    for line in _LINES:
        first = board[line[0][0]][line[0][1]]
        if first != EMPTY and all(board[r][c] == first for r, c in line):
            return first
    return None


def is_full(board: Board) -> bool:
    return all(cell != EMPTY for row in board for cell in row)


def _is_index(value: object) -> bool:
    # bool é subtipo de int em Python; coordenadas booleanas são inválidas.
    return type(value) is int and 0 <= value < BOARD_SIZE


@dataclass(frozen=True)
class Snapshot:
    """Fotografia imutável do estado oficial, consistente para ambos os jogadores."""

    game_id: str
    board: Board
    turn: str | None
    revision: int

    def board_as_lists(self) -> list[list[str]]:
        return [list(row) for row in self.board]


@dataclass(frozen=True)
class MoveOutcome:
    """Resultado de uma tentativa de jogada."""

    accepted: bool
    code: str | None = None
    message: str | None = None
    row: int | None = None
    col: int | None = None
    snapshot: Snapshot | None = None
    result: str | None = None  # "WIN" ou "DRAW" quando a jogada encerrou a partida
    winner: str | None = None

    @property
    def finished(self) -> bool:
        return self.result is not None


def _rejected(code: str, message: str) -> MoveOutcome:
    return MoveOutcome(accepted=False, code=code, message=message)


class Game:
    """Partida com exatamente dois participantes distintos (X e O)."""

    def __init__(self, game_id: str, player_x: str, player_o: str) -> None:
        if player_x == player_o:
            raise ValueError("Uma partida exige dois participantes distintos")
        self.game_id = game_id
        self._players = {"X": player_x, "O": player_o}
        self._board: Board = empty_board()
        self._turn: str | None = "X"
        self._revision = 0
        self._status = GameStatus.ACTIVE
        self._winner: str | None = None
        # Lock reentrante: o servidor o adquire para enfileirar mensagens na
        # mesma ordem lógica em que o estado foi alterado.
        self.lock = threading.RLock()

    @property
    def status(self) -> GameStatus:
        with self.lock:
            return self._status

    @property
    def winner(self) -> str | None:
        with self.lock:
            return self._winner

    @property
    def players(self) -> dict[str, str]:
        """Mapa marca -> identificador do participante."""

        return dict(self._players)

    def mark_of(self, player_id: str) -> str | None:
        for mark, owner in self._players.items():
            if owner == player_id:
                return mark
        return None

    def opponent_of(self, player_id: str) -> str | None:
        mark = self.mark_of(player_id)
        if mark is None:
            return None
        return self._players["O" if mark == "X" else "X"]

    def snapshot(self) -> Snapshot:
        with self.lock:
            return self._snapshot_locked()

    def _snapshot_locked(self) -> Snapshot:
        return Snapshot(self.game_id, self._board, self._turn, self._revision)

    def play(self, player_id: str, game_id: object, row: object, col: object) -> MoveOutcome:
        """Valida e aplica uma jogada de forma atômica.

        Uma rejeição nunca altera célula, turno, revisão, vencedor ou estado.
        """

        with self.lock:
            mark = self.mark_of(player_id)
            if mark is None or game_id != self.game_id:
                return _rejected("NOT_IN_GAME", "Você não participa desta partida")
            if self._status is not GameStatus.ACTIVE:
                return _rejected("GAME_FINISHED", "A partida já foi encerrada")
            if mark != self._turn:
                return _rejected("NOT_YOUR_TURN", "Não é a sua vez")
            if not _is_index(row) or not _is_index(col):
                return _rejected("INVALID_POSITION", "Linha e coluna devem estar entre 0 e 2")
            assert isinstance(row, int) and isinstance(col, int)
            if self._board[row][col] != EMPTY:
                return _rejected("OCCUPIED", "Posição já ocupada")

            rows = [list(line) for line in self._board]
            rows[row][col] = mark
            self._board = tuple(tuple(line) for line in rows)
            self._revision += 1

            result: str | None = None
            winner = find_winner(self._board)
            if winner is not None:
                result = "WIN"
                self._winner = winner
            elif is_full(self._board):
                result = "DRAW"
            if result is None:
                self._turn = "O" if mark == "X" else "X"
            else:
                self._turn = None
                self._status = GameStatus.FINISHED

            return MoveOutcome(
                accepted=True,
                row=row,
                col=col,
                snapshot=self._snapshot_locked(),
                result=result,
                winner=winner,
            )

    def abort(self) -> bool:
        """Marca a partida como abortada; ``True`` somente na transição real."""

        with self.lock:
            if self._status is not GameStatus.ACTIVE:
                return False
            self._status = GameStatus.ABORTED
            self._turn = None
            return True
