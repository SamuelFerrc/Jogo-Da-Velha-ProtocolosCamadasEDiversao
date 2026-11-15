"""Fila de espera e pareamento de jogadores."""

from __future__ import annotations

import itertools
import threading
from collections import deque
from typing import Protocol

from server.game import Game


class Participant(Protocol):
    """O que o lobby precisa saber de uma sessão."""

    client_id: str

    def is_connected(self) -> bool: ...


class Lobby:
    """Fila FIFO protegida por lock; o primeiro da fila recebe a marca X."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._queue: deque[Participant] = deque()
        self._game_counter = itertools.count(1)

    def join(self, participant: Participant) -> Game | None:
        """Enfileira o participante ou forma uma partida com o primeiro válido.

        Retorna ``None`` quando o participante ficou aguardando. Sessões já
        desconectadas são descartadas e nunca formam partida. Entrar duas vezes
        não duplica o participante na fila.
        """

        with self._lock:
            if any(waiting is participant for waiting in self._queue):
                return None
            while self._queue:
                opponent = self._queue.popleft()
                if opponent is participant or not opponent.is_connected():
                    continue
                game_id = f"g{next(self._game_counter)}"
                return Game(game_id, opponent.client_id, participant.client_id)
            self._queue.append(participant)
            return None

    def remove(self, participant: Participant) -> bool:
        """Retira o participante da fila; ``True`` se ele estava aguardando."""

        with self._lock:
            for index, waiting in enumerate(self._queue):
                if waiting is participant:
                    del self._queue[index]
                    return True
            return False

    def waiting_count(self) -> int:
        with self._lock:
            return len(self._queue)
