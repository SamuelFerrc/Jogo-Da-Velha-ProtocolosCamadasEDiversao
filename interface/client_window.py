"""Backend PySide6 da janela do cliente e do espelho textual."""

from __future__ import annotations

import argparse
import queue
import threading
from typing import Any

from PySide6.QtCore import QObject, Property, QCoreApplication, Signal, Slot

from interface.client_state import ClientPhase, ClientPresentationState, ClientStateError
from interface.qt_common import event_to_mapping, print_trace, run_qml_application
from shared.protocol import ProtocolError, make_message
from shared.telemetry import TraceEvent, emit_trace, trace_event
from shared.transport import MessageChannel, TransportError, connect_to_server


class ClientBackend(QObject):
    """Controlador único compartilhado pela janela QML e pelo PowerShell/CMD."""

    stateChanged = Signal()
    traceEventsChanged = Signal()
    _eventReceived = Signal(str, object)

    def __init__(
        self,
        host: str,
        port: int,
        *,
        console_enabled: bool = True,
    ) -> None:
        super().__init__()
        self.console_enabled = console_enabled
        self.state = ClientPresentationState()
        self.channel: MessageChannel | None = None
        self._outbox: queue.Queue[dict[str, Any] | None] | None = None
        self._network_stop = threading.Event()
        self._closing = False
        self._console_started = False
        self._console_condition = threading.Condition()
        self._host = host
        self._port_text = str(port)
        self._trace_events: list[dict[str, Any]] = []
        self._state_tick = 0
        self._eventReceived.connect(self._handle_event)

    # ---------------------------------------------------------------- propriedades QML

    def _get_host(self) -> str:
        return self._host

    def _set_host(self, value: str) -> None:
        value = value.strip()
        if value != self._host:
            self._host = value
            self.stateChanged.emit()

    host = Property(str, _get_host, _set_host, notify=stateChanged)

    def _get_port(self) -> str:
        return self._port_text

    def _set_port(self, value: str) -> None:
        if value != self._port_text:
            self._port_text = value
            self.stateChanged.emit()

    port = Property(str, _get_port, _set_port, notify=stateChanged)

    @Property(str, notify=stateChanged)
    def phaseLabel(self) -> str:  # noqa: N802 - propriedade exposta ao QML
        labels = {
            ClientPhase.DISCONNECTED: "DESCONECTADO",
            ClientPhase.CONNECTING: "CONECTANDO",
            ClientPhase.HANDSHAKE: "IDENTIFICANDO",
            ClientPhase.WAITING: "NO LOBBY",
            ClientPhase.IN_GAME: f"EM PARTIDA · {self.state.mark}",
            ClientPhase.ENDED: "PARTIDA ENCERRADA",
        }
        return labels[self.state.phase]

    @Property(str, notify=stateChanged)
    def notice(self) -> str:
        return self.state.notice

    @Property(str, notify=stateChanged)
    def mark(self) -> str:
        return self.state.mark

    @Property(str, notify=stateChanged)
    def gameId(self) -> str:  # noqa: N802
        return self.state.game_id

    @Property(str, notify=stateChanged)
    def gameTitle(self) -> str:  # noqa: N802
        return (
            "Tabuleiro oficial"
            if self.state.game_id == "—"
            else f"Partida {self.state.game_id}"
        )

    @Property(str, notify=stateChanged)
    def revisionLabel(self) -> str:  # noqa: N802
        return "—" if self.state.revision < 0 else str(self.state.revision)

    @Property(str, notify=stateChanged)
    def turnLabel(self) -> str:  # noqa: N802
        if self.state.turn is None and self.state.phase is ClientPhase.ENDED:
            return "FIM"
        return f"TURNO {self.state.turn or '—'}"

    @Property(str, notify=stateChanged)
    def connectionLabel(self) -> str:  # noqa: N802
        labels = {
            ClientPhase.DISCONNECTED: "TCP desconectado",
            ClientPhase.CONNECTING: "Abrindo socket TCP...",
            ClientPhase.HANDSHAKE: "TCP conectado · HELLO",
            ClientPhase.WAITING: "TCP conectado · lobby",
            ClientPhase.IN_GAME: "TCP conectado · em partida",
            ClientPhase.ENDED: "TCP conectado · sessão aberta",
        }
        return labels[self.state.phase]

    @Property(bool, notify=stateChanged)
    def connected(self) -> bool:
        return self.state.phase is not ClientPhase.DISCONNECTED

    @Property(bool, notify=stateChanged)
    def canConnect(self) -> bool:  # noqa: N802
        return self.state.phase is ClientPhase.DISCONNECTED

    @Property(bool, notify=stateChanged)
    def canPlayAgain(self) -> bool:  # noqa: N802
        return self.state.phase is ClientPhase.ENDED

    @Property(int, notify=stateChanged)
    def stateTick(self) -> int:  # noqa: N802
        return self._state_tick

    @Property("QVariantList", notify=traceEventsChanged)
    def traceEvents(self) -> list[dict[str, Any]]:  # noqa: N802
        return list(self._trace_events)

    @Slot(int, int, result=str)
    def cellAt(self, row: int, col: int) -> str:  # noqa: N802
        if row not in range(3) or col not in range(3):
            return ""
        return self.state.board[row][col]

    @Slot(int, int, result=bool)
    def canPlay(self, row: int, col: int) -> bool:  # noqa: N802
        return self.state.can_play(row, col)

    # ---------------------------------------------------------------- comandos públicos

    @Slot()
    def startConsole(self) -> None:  # noqa: N802
        if not self.console_enabled or self._console_started:
            return
        self._console_started = True
        threading.Thread(
            target=self._console_loop,
            name="tttp-client-console",
            daemon=True,
        ).start()

    @Slot()
    def connectToServer(self) -> None:  # noqa: N802
        if self.state.phase is not ClientPhase.DISCONNECTED:
            self._set_notice("Já existe uma conexão ou tentativa em andamento.")
            return
        try:
            port = int(self._port_text)
            if port not in range(1, 65536):
                raise ValueError
        except ValueError:
            self._set_notice("Porta inválida; use um inteiro entre 1 e 65535.")
            return
        host = self._host.strip()
        if not host:
            self._set_notice("Informe o host do servidor.")
            return
        self.state.begin_connection()
        self._network_stop.clear()
        self._application_event(
            "INTERNO",
            "Solicitação de conexão",
            detail=f"A aplicação cliente pediu ao transporte para conectar em {host}:{port}.",
        )
        self._refresh()
        threading.Thread(
            target=self._network_loop,
            args=(host, port),
            name="tttp-client-network",
            daemon=True,
        ).start()

    @Slot(int, int)
    def play(self, row: int, col: int) -> None:
        try:
            self.state.mark_move_sent(row, col)
        except ClientStateError as exc:
            self._set_notice(str(exc))
            return
        self._send(
            make_message("MOVE", game_id=self.state.game_id, row=row, col=col),
            "A aplicação envia apenas a intenção; marca, turno e tabuleiro não são enviados.",
        )
        self._refresh()

    @Slot()
    def playAgain(self) -> None:  # noqa: N802
        try:
            self.state.prepare_rejoin()
        except ClientStateError as exc:
            self._set_notice(str(exc))
            return
        self._send(
            make_message("JOIN"),
            "A sessão TCP é reutilizada; a partida encerrada não é reaberta.",
        )
        self._refresh()

    @Slot()
    def disconnectFromServer(self) -> None:  # noqa: N802
        channel = self.channel
        outbox = self._outbox
        if channel is not None and outbox is not None and not channel.closed:
            message = make_message("QUIT")
            self._application_event(
                "SAIDA",
                "Encerramento solicitado",
                message=message,
                detail="QUIT encerra a sessão; não existe mensagem BYE no TTTP/1.",
            )
            try:
                channel.send_message(message)
            except (TransportError, ProtocolError):
                pass
        self._network_stop.set()
        if outbox is not None:
            outbox.put(None)
        if channel is not None:
            channel.close()
        self.channel = None
        self._outbox = None
        self.state.reset()
        self._refresh()

    @Slot()
    def shutdown(self) -> None:
        if self._closing:
            return
        self._closing = True
        self.disconnectFromServer()

    # ---------------------------------------------------------------- comunicação

    def _network_loop(self, host: str, port: int) -> None:
        try:
            channel = connect_to_server(
                host,
                port,
                timeout=5,
                trace_observer=self._trace,
                trace_actor="Cliente / transporte",
                trace_peer=f"Servidor {host}:{port}",
            )
            outbox: queue.Queue[dict[str, Any] | None] = queue.Queue()
            self._eventReceived.emit("connected", (channel, outbox))
            threading.Thread(
                target=self._writer_loop,
                args=(channel, outbox),
                name="tttp-client-writer",
                daemon=True,
            ).start()
            while not self._network_stop.is_set():
                self._eventReceived.emit("message", channel.receive_message())
        except (TransportError, ProtocolError) as exc:
            if not self._network_stop.is_set():
                self._eventReceived.emit("network_error", str(exc))

    def _writer_loop(
        self,
        channel: MessageChannel,
        outbox: queue.Queue[dict[str, Any] | None],
    ) -> None:
        while not self._network_stop.is_set():
            payload = outbox.get()
            if payload is None:
                return
            try:
                channel.send_message(payload)
            except (TransportError, ProtocolError) as exc:
                if not self._network_stop.is_set():
                    self._eventReceived.emit("network_error", str(exc))
                return

    def _send(self, message: dict[str, Any], detail: str) -> None:
        if self._outbox is None or self.channel is None:
            self._set_notice("Não há canal TCP conectado.")
            return
        self._application_event(
            "SAIDA",
            "Comando construído e validado",
            message=message,
            detail=detail,
        )
        self._outbox.put(message)

    @Slot(str, object)
    def _handle_event(self, kind: str, value: object) -> None:
        if self._closing and kind not in {"trace", "quit"}:
            return
        if kind == "trace":
            assert isinstance(value, TraceEvent)
            self._trace_events = [*self._trace_events[-199:], event_to_mapping(value)]
            self.traceEventsChanged.emit()
            return
        if kind == "connected":
            self.channel, self._outbox = value  # type: ignore[misc]
            try:
                self.state.connection_established()
            except ClientStateError as exc:
                self._set_notice(str(exc))
                return
            self._application_event(
                "SAIDA",
                "Handshake iniciado",
                message=make_message("HELLO"),
                detail="A conexão TCP existe; agora começa o diálogo da aplicação TTTP/1.",
            )
            assert self._outbox is not None
            self._outbox.put(make_message("HELLO"))
            self._refresh()
            return
        if kind == "message":
            assert isinstance(value, dict)
            self._handle_message(value)
            return
        if kind == "network_error":
            self._application_event(
                "INTERNO",
                "Falha de comunicação",
                detail=f"Erro de transporte: {value}",
            )
            self._network_stop.set()
            if self.channel is not None:
                self.channel.close()
            self.channel = None
            self._outbox = None
            self.state.reset(f"Conexão encerrada: {value}")
            self._refresh()
            return
        if kind == "console_action":
            action, args = value  # type: ignore[misc]
            getattr(self, action)(*args)
            return
        if kind == "quit":
            QCoreApplication.quit()

    def _handle_message(self, message: dict[str, Any]) -> None:
        self._application_event(
            "ENTRADA",
            "Mensagem entregue à camada de aplicação",
            message=message,
            detail="O transporte já removeu LF, decodificou UTF-8/JSON e validou o payload.",
        )
        try:
            description = self.state.apply_server_message(message)
        except (ClientStateError, ProtocolError) as exc:
            self._application_event(
                "INTERNO",
                "Sequência recusada pela aplicação",
                message=message,
                detail=f"Erro de estado: {exc}",
            )
            self._set_notice(f"Protocolo inconsistente: {exc}")
            return
        self._application_event(
            "INTERNO",
            "Estado de apresentação atualizado",
            message=message,
            detail=description,
        )
        if message["type"] == "WELCOME":
            self._send(
                make_message("JOIN"),
                "WELCOME aceito; a aplicação solicita entrada no lobby.",
            )
        if message["type"] == "BOARD" and self.console_enabled:
            self._print_board()
        self._refresh()

    # ---------------------------------------------------------------- telemetria e console

    def _trace(self, event: TraceEvent) -> None:
        if self.console_enabled:
            print_trace(event)
        self._eventReceived.emit("trace", event)

    def _application_event(
        self,
        direction: str,
        action: str,
        *,
        message: dict[str, Any] | None = None,
        detail: str = "",
    ) -> None:
        emit_trace(
            self._trace,
            trace_event(
                layer="APLICACAO",
                direction=direction,  # type: ignore[arg-type]
                action=action,
                actor="Cliente / aplicação",
                peer="Servidor",
                message_type=None if message is None else message["type"],
                payload=message,
                detail=detail,
            ),
        )

    def _refresh(self) -> None:
        self._state_tick += 1
        self.stateChanged.emit()
        with self._console_condition:
            self._console_condition.notify_all()

    def _set_notice(self, notice: str) -> None:
        self.state.notice = notice
        self._refresh()

    def _print_board(self) -> None:
        print("\nTabuleiro oficial:")
        for index, row in enumerate(self.state.board):
            print(" " + " | ".join(cell or " " for cell in row))
            if index < 2:
                print("---+---+---")
        print(f"Revisão {self.state.revision} · turno {self.state.turn}\n", flush=True)

    def _console_loop(self) -> None:
        last_prompt: ClientPhase | None = None
        while not self._closing:
            phase = self.state.phase
            try:
                if phase is ClientPhase.DISCONNECTED:
                    if last_prompt is not phase:
                        print("\n================================")
                        print("          JOGO DA VELHA")
                        print("================================")
                        print("1 - Conectar e jogar")
                        print("2 - Sair")
                    last_prompt = phase
                    choice = input("\nEscolha uma opção (a janela usa o mesmo controle): ").strip()
                    if choice == "1":
                        self._eventReceived.emit("console_action", ("connectToServer", ()))
                    elif choice == "2":
                        self._eventReceived.emit("quit", None)
                    else:
                        print("Opção inválida! Escolha 1 ou 2.")
                elif (
                    phase is ClientPhase.IN_GAME
                    and self.state.turn == self.state.mark
                    and self.state.pending_move is None
                ):
                    last_prompt = phase
                    row = int(input("Escolha a linha (1 a 3): ")) - 1
                    col = int(input("Escolha a coluna (1 a 3): ")) - 1
                    self._eventReceived.emit("console_action", ("play", (row, col)))
                elif phase is ClientPhase.ENDED:
                    last_prompt = phase
                    choice = input("Jogar novamente? (s/n): ").strip().lower()
                    action = "playAgain" if choice in {"s", "sim"} else "disconnectFromServer"
                    self._eventReceived.emit("console_action", (action, ()))
                else:
                    last_prompt = phase
                    with self._console_condition:
                        self._console_condition.wait(timeout=0.5)
            except (EOFError, KeyboardInterrupt):
                self._eventReceived.emit("quit", None)
                return
            except ValueError:
                print("Digite apenas números inteiros entre 1 e 3.")


def run_client_app(host: str, port: int, *, console_enabled: bool = True) -> None:
    backend = ClientBackend(host, port, console_enabled=console_enabled)
    run_qml_application(backend, "ClientWindow.qml")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Interface gráfica do cliente TTTP/1")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--no-console", action="store_true")
    args = parser.parse_args(argv)
    run_client_app(args.host, args.port, console_enabled=not args.no_console)


if __name__ == "__main__":
    main()
