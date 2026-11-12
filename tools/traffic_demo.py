"""Gera uma troca TTTP/1 curta e observável em uma conexão TCP real."""

from __future__ import annotations

import argparse
import queue
import threading
import time
from collections.abc import Callable

from shared import (
    MessageChannel,
    accept_connection,
    connect_to_server,
    create_listening_socket,
    handle_heartbeat_message,
    make_message,
    validate_client_message,
    validate_server_message,
)

Transcript = list[tuple[str, str]]


def run_demo(host: str = "127.0.0.1", port: int = 5000, delay: float = 0.5) -> Transcript:
    """Executa HELLO/WELCOME, PING/PONG e QUIT em loopback.

    A porta 0 solicita uma porta efêmera ao sistema e é útil em testes. Para
    captura com Wireshark, prefira uma porta fixa como 5000.
    """

    if delay < 0:
        raise ValueError("delay não pode ser negativo")

    listener = create_listening_socket(host, port, backlog=1)
    actual_port = listener.getsockname()[1]
    transcript: Transcript = []
    errors: queue.Queue[BaseException] = queue.Queue()
    transcript_lock = threading.Lock()

    def record(side: str, message_type: str) -> None:
        with transcript_lock:
            transcript.append((side, message_type))

    def server_worker() -> None:
        channel: MessageChannel | None = None
        try:
            channel, _ = accept_connection(listener)

            hello = channel.receive_message()
            validate_client_message(hello)
            record("servidor recebeu", hello["type"])
            time.sleep(delay)

            welcome = make_message("WELCOME", client_id="c-demo")
            channel.send_message(welcome)
            record("servidor enviou", welcome["type"])

            ping = channel.receive_message()
            validate_client_message(ping)
            record("servidor recebeu", ping["type"])
            time.sleep(delay)
            if handle_heartbeat_message(channel, ping):
                record("servidor enviou", "PONG")

            quit_message = channel.receive_message()
            validate_client_message(quit_message)
            record("servidor recebeu", quit_message["type"])
        except BaseException as exc:
            errors.put(exc)
        finally:
            if channel is not None:
                channel.close()

    server_thread = threading.Thread(target=server_worker, name="tttp-demo-server")
    server_thread.start()

    client: MessageChannel | None = None
    try:
        client = connect_to_server(host, actual_port, timeout=2)

        hello = make_message("HELLO")
        client.send_message(hello)
        record("cliente enviou", hello["type"])

        welcome = client.receive_message()
        validate_server_message(welcome)
        record("cliente recebeu", welcome["type"])
        time.sleep(delay)

        ping = make_message("PING")
        client.send_message(ping)
        record("cliente enviou", ping["type"])

        pong = client.receive_message()
        validate_server_message(pong)
        record("cliente recebeu", pong["type"])
        time.sleep(delay)

        quit_message = make_message("QUIT")
        client.send_message(quit_message)
        record("cliente enviou", quit_message["type"])
    finally:
        if client is not None:
            client.close()
        server_thread.join(timeout=5)
        listener.close()

    if server_thread.is_alive():
        raise RuntimeError("A thread de demonstração não encerrou")
    if not errors.empty():
        raise errors.get()
    return transcript


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Gera tráfego TTTP/1 para inspeção no Wireshark."
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="intervalo em segundos entre etapas observáveis",
    )
    return parser


def main(print_line: Callable[[str], None] = print) -> int:
    args = _build_parser().parse_args()
    transcript = run_demo(args.host, args.port, args.delay)
    for side, message_type in transcript:
        print_line(f"{side}: {message_type}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
