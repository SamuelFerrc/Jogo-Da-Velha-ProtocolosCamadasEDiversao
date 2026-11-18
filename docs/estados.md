# Máquinas de estados

Há dois conjuntos de estados distintos: o da **sessão** (por conexão) e o da **partida** (por `game_id`). Nenhum deles é uma mensagem de transporte.

## 1. Sessão (servidor)

```text
CONECTADO ──HELLO/WELCOME──▶ IDENTIFICADO ──JOIN──▶ AGUARDANDO
                                                     │
                                            START + BOARD
                                                     ▼
                                                EM_PARTIDA
                                                     │ GAME_OVER
                                                     ▼
                                                ENCERRADO
                                                     │
                               novo JOIN ─────────────┘
                               (retorna a AGUARDANDO)
```

| Estado | Entrada válida | Efeito | Entrada inválida |
|---|---|---|---|
| `CONECTADO` | `HELLO` | `WELCOME(client_id)` → `IDENTIFICADO`; remove o timeout de handshake | `JOIN` → `ERROR(INVALID_STATE)`; silêncio por mais que `--handshake-timeout` fecha a conexão |
| `IDENTIFICADO` | `JOIN` | `AGUARDANDO`; sem adversário → `WAITING`; com adversário → `START` e `BOARD` aos dois | `HELLO` → `ERROR(INVALID_STATE)` |
| `AGUARDANDO` | (aguarda pareamento) | `START` + `BOARD` inicial → `EM_PARTIDA` | `JOIN`/`HELLO` → `ERROR(INVALID_STATE)` |
| `EM_PARTIDA` | `MOVE` | ver §2 | `JOIN`/`HELLO` → `ERROR(INVALID_STATE)` |
| `ENCERRADO` | `JOIN` (nova partida) | volta a `AGUARDANDO`; o próximo pareamento usa novo `game_id` | `MOVE` → `MOVE_RESULT(REJECTED, GAME_FINISHED)` |

Em **qualquer** estado: `QUIT`, EOF ou falha de socket levam a `DESCONECTADO` (sessão removida do lobby e partida ativa abortada). `UNSUPPORTED_VERSION` e `MESSAGE_TOO_LARGE` também fecham a conexão. `MOVE` fora de partida → `MOVE_RESULT(REJECTED, NOT_IN_GAME)`.

O retorno de `ENCERRADO` a `AGUARDANDO` reaproveita somente a conexão e a
sessão. A partida anterior permanece terminal, e o lobby não garante parear os
mesmos participantes.

## 2. Partida (servidor)

```text
ATIVA ──jogada aceita sem fim──▶ ATIVA (turno alterna, revision+1)
ATIVA ──WIN ou DRAW────────────▶ FINALIZADA (turn = null)
ATIVA ──QUIT/EOF de um jogador─▶ ABORTADA   (turn = null)
```

`FINALIZADA` e `ABORTADA` são terminais: nenhuma jogada altera a partida.

## 3. Sequência de uma jogada aceita

```text
Cliente X            Servidor                     Cliente O
   │── MOVE ────────▶ │ (lock da partida: valida, aplica, snapshot, enfileira)
   │◀─ MOVE_RESULT ── │
   │◀─ BOARD ──────── │ ─────── BOARD ────────────▶ │
   │◀─ GAME_OVER* ─── │ ─────── GAME_OVER* ───────▶ │      * só se a jogada encerrou
```

Uma jogada rejeitada produz apenas `MOVE_RESULT(REJECTED, code)` ao solicitante.

## 4. Estados do cliente

Ver o diagrama de AGENTS.md §6.1 e [cliente.md](cliente.md). O estado do cliente é apenas de apresentação; a fonte de verdade é o servidor.
