"""Backend PySide6 do painel do servidor TTTP/1."""

from __future__ import annotations

import argparse
from typing import Any

from PySide6.QtCore import QObject, Property, QTimer, Signal, Slot

from interface.qt_common import event_to_mapping, print_trace, run_qml_application
from server.server import DEFAULT_HANDSHAKE_TIMEOUT, GameServer
from shared.telemetry import TraceEvent
from shared.transport import TransportError


class ServerBackend(QObject):
    """Expõe ao QML somente a fotografia observável do GameServer real."""

    stateChanged = Signal()
    traceEventsChanged = Signal()
    _traceReceived = Signal(object)

    def __init__(
        self,
        host: str,
        port: int,
        *,
        handshake_timeout: float | None = DEFAULT_HANDSHAKE_TIMEOUT,
        console_enabled: bool = True,
    ) -> None:
        super().__init__()
        self.host = host
        self.port = port
        self.handshake_timeout = handshake_timeout
        self.console_enabled = console_enabled
        self.server: GameServer | None = None
        self._closing = False
        self._server_state = "INICIANDO"
        self._address = "—"
        self._sessions: list[dict[str, Any]] = []
        self._session_count = 0
        self._waiting_count = 0
        self._game_count = 0
        self._game_summary = "Nenhuma partida ativa"
        self._explanation = "O servidor abrirá o listener TCP e aguardará HELLO."
        self._trace_events: list[dict[str, Any]] = []
        self._traceReceived.connect(self._append_trace)
        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(100)
        self._poll_timer.timeout.connect(self._refresh_snapshot)
        self._poll_timer.start()

    # ---------------------------------------------------------------- propriedades QML

    @Property(str, notify=stateChanged)
    def statusLabel(self) -> str:  # noqa: N802
        if self.server is not None:
            return f"ONLINE · {self._address.replace('Escutando em ', '')}"
        return self._server_state

    @Property(str, notify=stateChanged)
    def actionLabel(self) -> str:  # noqa: N802
        return "Parar servidor" if self.server is not None else "Iniciar servidor"

    @Property(bool, notify=stateChanged)
    def serverRunning(self) -> bool:  # noqa: N802
        return self.server is not None

    @Property(str, notify=stateChanged)
    def addressLabel(self) -> str:  # noqa: N802
        return self._address

    @Property(str, notify=stateChanged)
    def handshakeLabel(self) -> str:  # noqa: N802
        return (
            "sem limite"
            if self.handshake_timeout is None
            else f"{self.handshake_timeout:g} s"
        )

    @Property(int, notify=stateChanged)
    def sessionCount(self) -> int:  # noqa: N802
        return self._session_count

    @Property(int, notify=stateChanged)
    def waitingCount(self) -> int:  # noqa: N802
        return self._waiting_count

    @Property(int, notify=stateChanged)
    def gameCount(self) -> int:  # noqa: N802
        return self._game_count

    @Property(str, notify=stateChanged)
    def gameSummary(self) -> str:  # noqa: N802
        return self._game_summary

    @Property(str, notify=stateChanged)
    def explanation(self) -> str:
        return self._explanation

    @Property("QVariantList", notify=stateChanged)
    def sessions(self) -> list[dict[str, Any]]:
        return list(self._sessions)

    @Property("QVariantList", notify=traceEventsChanged)
    def traceEvents(self) -> list[dict[str, Any]]:  # noqa: N802
        return list(self._trace_events)

    # ---------------------------------------------------------------- ciclo do servidor

    @Slot()
    def toggleServer(self) -> None:  # noqa: N802
        if self.server is None:
            self.startServer()
        else:
            self.stopServer()

    @Slot()
    def startServer(self) -> None:  # noqa: N802
        if self.server is not None:
            return
        candidate = GameServer(
            self.host,
            self.port,
            handshake_timeout=self.handshake_timeout,
            trace_observer=self._trace,
        )
        try:
            address = candidate.start()
        except TransportError as exc:
            self._explanation = f"Não foi possível iniciar: {exc}"
            self._server_state = "ERRO"
            self.stateChanged.emit()
            return
        self.server = candidate
        self._server_state = "ONLINE"
        self._address = f"Escutando em {address[0]}:{address[1]}"
        self._explanation = (
            "Listener ativo. Conexões recebem uma sessão; HELLO inicia o handshake TTTP/1."
        )
        self.stateChanged.emit()

    @Slot()
    def stopServer(self) -> None:  # noqa: N802
        server = self.server
        if server is None:
            return
        self._server_state = "ENCERRANDO"
        self.stateChanged.emit()
        server.stop()
        self.server = None
        self._server_state = "OFFLINE"
        self._address = "—"
        self._sessions = []
        self._session_count = 0
        self._waiting_count = 0
        self._game_count = 0
        self._game_summary = "Nenhuma partida ativa"
        self._explanation = (
            "Servidor parado. O mesmo endereço da linha de comando pode ser iniciado novamente."
        )
        self.stateChanged.emit()

    @Slot()
    def shutdown(self) -> None:
        if self._closing:
            return
        self._closing = True
        self._poll_timer.stop()
        if self.server is not None:
            self.server.stop()
            self.server = None

    # ---------------------------------------------------------------- telemetria e fotografia

    def _trace(self, event: TraceEvent) -> None:
        if self.console_enabled:
            print_trace(event)
        self._traceReceived.emit(event)

    @Slot(object)
    def _append_trace(self, event: object) -> None:
        if not isinstance(event, TraceEvent):
            return
        self._trace_events = [*self._trace_events[-199:], event_to_mapping(event)]
        self.traceEventsChanged.emit()

    @Slot()
    def _refresh_snapshot(self) -> None:
        server = self.server
        if server is None:
            return
        snapshot = server.status_snapshot()
        sessions = snapshot["sessions"]
        games = snapshot["games"]
        game_summary = "Nenhuma partida ativa"
        if games:
            game = games[0]
            turn = game["turn"] or "—"
            extra = "" if len(games) == 1 else f" · +{len(games) - 1} partida(s)"
            game_summary = (
                f"{game['game_id']} · revisão {game['revision']} · turno {turn}{extra}"
            )
        changed = (
            sessions != self._sessions
            or snapshot["session_count"] != self._session_count
            or snapshot["waiting_count"] != self._waiting_count
            or snapshot["game_count"] != self._game_count
            or game_summary != self._game_summary
        )
        if not changed:
            return
        self._sessions = sessions
        self._session_count = snapshot["session_count"]
        self._waiting_count = snapshot["waiting_count"]
        self._game_count = snapshot["game_count"]
        self._game_summary = game_summary
        self.stateChanged.emit()


def run_server_app(
    host: str,
    port: int,
    *,
    handshake_timeout: float | None = DEFAULT_HANDSHAKE_TIMEOUT,
    console_enabled: bool = True,
) -> None:
    backend = ServerBackend(
        host,
        port,
        handshake_timeout=handshake_timeout,
        console_enabled=console_enabled,
    )
    run_qml_application(backend, "ServerWindow.qml")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Interface gráfica do servidor TTTP/1")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--handshake-timeout", type=float, default=DEFAULT_HANDSHAKE_TIMEOUT)
    parser.add_argument("--no-console", action="store_true")
    args = parser.parse_args(argv)
    run_server_app(
        args.host,
        args.port,
        handshake_timeout=args.handshake_timeout,
        console_enabled=not args.no_console,
    )


if __name__ == "__main__":
    main()
