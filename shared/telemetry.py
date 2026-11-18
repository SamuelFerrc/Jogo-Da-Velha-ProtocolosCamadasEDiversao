"""Eventos opcionais para explicar as camadas sem alterar o protocolo TTTP/1.

A telemetria é local: nenhum campo é acrescentado às mensagens na rede. Um
observador defeituoso também nunca pode interromper a comunicação principal.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, Literal, TypeAlias

LayerName: TypeAlias = Literal["APLICACAO", "TRANSPORTE"]
DirectionName: TypeAlias = Literal["ENTRADA", "SAIDA", "INTERNO"]


@dataclass(frozen=True, slots=True)
class TraceEvent:
    """Registro imutável de uma etapa local da comunicação."""

    timestamp: float
    layer: LayerName
    direction: DirectionName
    action: str
    actor: str
    peer: str = ""
    message_type: str | None = None
    payload: Mapping[str, Any] | None = None
    detail: str = ""
    byte_count: int | None = None
    buffered_bytes: int | None = None


TraceObserver: TypeAlias = Callable[[TraceEvent], None]


def trace_event(
    *,
    layer: LayerName,
    direction: DirectionName,
    action: str,
    actor: str,
    peer: str = "",
    message_type: str | None = None,
    payload: Mapping[str, Any] | None = None,
    detail: str = "",
    byte_count: int | None = None,
    buffered_bytes: int | None = None,
) -> TraceEvent:
    """Cria um evento com uma cópia rasa e estável do payload."""

    normalized_payload = dict(payload) if payload is not None else None
    return TraceEvent(
        timestamp=time.time(),
        layer=layer,
        direction=direction,
        action=action,
        actor=actor,
        peer=peer,
        message_type=message_type,
        payload=normalized_payload,
        detail=detail,
        byte_count=byte_count,
        buffered_bytes=buffered_bytes,
    )


def emit_trace(observer: TraceObserver | None, event: TraceEvent) -> None:
    """Entrega um evento sem permitir que a observabilidade quebre o jogo."""

    if observer is None:
        return
    try:
        observer(event)
    except Exception:  # noqa: BLE001 - telemetria é deliberadamente best effort
        return


__all__ = [
    "DirectionName",
    "LayerName",
    "TraceEvent",
    "TraceObserver",
    "emit_trace",
    "trace_event",
]
