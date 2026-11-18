"""Infraestrutura comum das interfaces PySide6/QML do TTTP/1."""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import PySide6
from PySide6.QtCore import QUrl
from PySide6.QtGui import QFont, QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

from shared.telemetry import TraceEvent

QML_DIR = Path(__file__).with_name("qml")
_PYSIDE_DLL_DIRECTORY = (
    os.add_dll_directory(str(Path(PySide6.__file__).parent))
    if sys.platform == "win32" and hasattr(os, "add_dll_directory")
    else None
)


def event_to_mapping(event: TraceEvent) -> dict[str, Any]:
    """Converte um evento imutável em dados simples consumíveis pelo QML."""

    direction = {"ENTRADA": "←", "SAIDA": "→", "INTERNO": "•"}[event.direction]
    payload = (
        ""
        if event.payload is None
        else json.dumps(event.payload, ensure_ascii=False, separators=(",", ":"))
        + r"\n"
    )
    metrics: list[str] = []
    if event.byte_count is not None:
        metrics.append(f"{event.byte_count} bytes")
    if event.buffered_bytes is not None:
        metrics.append(f"buffer residual {event.buffered_bytes}")
    return {
        "time": time.strftime("%H:%M:%S", time.localtime(event.timestamp)),
        "layer": "APLICAÇÃO" if event.layer == "APLICACAO" else "TRANSPORTE",
        "direction": direction,
        "action": event.action,
        "messageType": event.message_type or "",
        "peer": event.peer,
        "detail": event.detail,
        "metrics": " · ".join(metrics),
        "payload": payload,
        "application": event.layer == "APLICACAO",
        "error": "erro" in event.detail.lower() or "falha" in event.detail.lower(),
    }


def print_trace(event: TraceEvent) -> None:
    """Mantém no PowerShell/CMD o mesmo evento mostrado pelo QML."""

    direction = {"ENTRADA": "<-", "SAIDA": "->", "INTERNO": ".."}[event.direction]
    kind = f" {event.message_type}" if event.message_type else ""
    print(f"[{event.layer}] {direction} {event.action}{kind}: {event.detail}", flush=True)
    if event.payload is not None:
        print(
            json.dumps(event.payload, ensure_ascii=False, separators=(",", ":"))
            + r"\n",
            flush=True,
        )


def run_qml_application(backend: Any, qml_name: str) -> int:
    """Carrega uma janela QML com um backend Python já construído."""

    QQuickStyle.setStyle("Basic")
    app = QGuiApplication.instance()
    owns_app = app is None
    if app is None:
        app = QGuiApplication([sys.argv[0]])
    app.setApplicationName("TTTP/1 · Jogo da Velha")
    app.setOrganizationName("UESC")
    app.setFont(QFont("Segoe UI", 10))

    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("backend", backend)
    qml_path = QML_DIR / qml_name
    engine.load(QUrl.fromLocalFile(str(qml_path)))
    if not engine.rootObjects():
        raise RuntimeError(f"Não foi possível carregar a interface QML: {qml_path}")

    app.aboutToQuit.connect(backend.shutdown)
    result = app.exec() if owns_app else 0
    del engine
    return result


__all__ = [
    "QML_DIR",
    "event_to_mapping",
    "print_trace",
    "run_qml_application",
]
