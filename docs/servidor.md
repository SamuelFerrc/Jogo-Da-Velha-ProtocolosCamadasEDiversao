# Servidor

O servidor é a **única autoridade** sobre a partida: define `game_id`, marcas X/O, tabuleiro, turno, `revision` e resultado. Nada que o cliente informe (`mark`, `turn`, `winner`, `client_id`) é usado para autenticar ações. O contrato de mensagens está em [protocolo.md](protocolo.md); o enquadramento TCP, em [transporte.md](transporte.md).

## 1. Módulos

| Arquivo | Responsabilidade |
|---|---|
| `server/game.py` | Regras puras e estado da partida (`Game`, `Snapshot`, `MoveOutcome`, `find_winner`, `is_full`). Não usa sockets nem mensagens. |
| `server/lobby.py` | Fila FIFO com lock, pareamento, atribuição X/O (o primeiro da fila é X) e `game_id` sequencial (`g1`, `g2`, ...). |
| `server/server.py` | `GameServer`: `listen`/`accept`, sessões, roteamento de mensagens, envio ordenado e ciclo de vida. |

## 2. Execução

```bash
python -m server.server --host 127.0.0.1 --port 5000
```

| Parâmetro | Padrão | Significado |
|---|---|---|
| `--host` | `127.0.0.1` | Interface de escuta. Use `0.0.0.0` apenas se os clientes estiverem em outra máquina. |
| `--port` | `5000` | Porta TCP. |
| `--handshake-timeout` | `30` | Segundos para o cliente enviar `HELLO`. Não se aplica ao tempo de reflexão das jogadas. |
| `--log-level` | `INFO` | Nível do `logging` (conexão, pareamento, jogadas, erros, término, EOF). |
| `--gui` | automático em TTY | Força o painel gráfico mesmo fora de um terminal interativo. |
| `--terminal-only` | desativado | Mantém somente o servidor textual legado. |

Em um PowerShell/CMD interativo, o comando padrão abre também o painel em
`interface/server_window.py`. O terminal continua recebendo o espelho textual
dos eventos. O painel usa a mesma instância de `GameServer` e mostra listener,
sessões, lobby, partidas, decisões da aplicação e os registros processados por
`shared.transport`; não existe um servidor gráfico separado.

## 3. Concorrência

- Cada conexão tem **uma thread de leitura** e **uma thread de escrita**. Um cliente lento ou parado nunca bloqueia o outro.
- Todo envio passa por uma **fila de saída por sessão**. As mensagens de uma jogada são enfileiradas enquanto o **lock da partida** está retido; a rede só é usada depois, pela thread de escrita. Assim `MOVE_RESULT`, `BOARD` e `GAME_OVER` chegam em ordem lógica e nenhuma operação de rede bloqueante ocorre com o lock retido.
- `Game.play` valida, aplica e gera o snapshot de forma atômica. Duas jogadas simultâneas no mesmo turno resultam em **uma** aceita e **uma** rejeitada (`NOT_YOUR_TURN`).
- O pareamento (`Lobby.join` + início da partida) é serializado por um lock de matchmaking; o lobby tem lock próprio.
- Ordem de aquisição dos locks: matchmaking → lobby; partida → registro de sessões. Nenhum caminho adquire na ordem inversa.

## 4. Tratamento de mensagens

| Situação | Resposta | Sessão |
|---|---|---|
| JSON/UTF-8 inválido, campo ausente ou de tipo errado (inclusive `row`/`col` booleano, fracionário, string ou lista) | `ERROR(BAD_FORMAT)` | mantida |
| Tipo desconhecido | `ERROR(UNKNOWN_TYPE)` | mantida |
| Tipo válido, mas só servidor→cliente (ex.: `WAITING` enviado pelo cliente) | `ERROR(BAD_FORMAT)` | mantida |
| `version` ≠ 1 | `ERROR(UNSUPPORTED_VERSION)` | fechada após enviar |
| Registro > 4096 bytes | `ERROR(MESSAGE_TOO_LARGE)` | fechada após enviar |
| `HELLO` repetido; `JOIN` antes de `HELLO` ou já aguardando/em partida | `ERROR(INVALID_STATE)` | mantida |
| `MOVE` fora de partida ou com `game_id` alheio | `MOVE_RESULT(REJECTED, NOT_IN_GAME)` | mantida |
| `MOVE` fora do turno / posição fora de 0..2 / célula ocupada / partida encerrada | `MOVE_RESULT(REJECTED, NOT_YOUR_TURN \| INVALID_POSITION \| OCCUPIED \| GAME_FINISHED)` | mantida |
| `PING` | `PONG` | mantida |
| `QUIT`, EOF ou falha de socket | nenhuma (ver §5) | encerrada |

Rejeições semânticas de `MOVE` usam **somente** `MOVE_RESULT`; nunca também `ERROR`. Uma rejeição não altera célula, turno, `revision` nem estado.

A ordem de validação de um `MOVE` é: participação e `game_id` → partida ativa → turno → índices → célula livre.

## 5. Desconexões

- `QUIT`/EOF/queda **no lobby**: a sessão é removida da fila; nunca se forma partida com sessão desconectada.
- `QUIT`/EOF/queda **em partida ativa**: a partida passa a `ABORTADA` e o adversário recebe `GAME_OVER(result=ABORTED, winner=null, reason=OPPONENT_LEFT)`. Abandono não conta como vitória.
- Saída **depois** de `GAME_OVER(WIN|DRAW)`: nenhum aviso adicional.
- Falha ao enviar a um socket já fechado é registrada no log e não afeta a partida do adversário.
- Se um participante cai entre o pareamento e o envio do `START`, a partida é abortada e o outro recebe `ABORTED`.

## 6. Nova partida na mesma conexão

O cliente oferece essa operação como “revanche”, enviando `JOIN` na mesma
conexão após `GAME_OVER`. O servidor aceita `JOIN` no estado
`ENCERRADO`: a sessão volta a `AGUARDANDO`, entra no lobby e, ao ser
pareada, recebe novo `START` com **novo `game_id`** e `BOARD` com
`revision` 0. As marcas **não** são preservadas, pois o primeiro da nova fila
recebe X. Não há reentrada em partida antiga e nenhuma mensagem nova foi
criada.

Esse comportamento é uma extensão compatível do ciclo da sessão e está
registrado em `AGENTS.md`, `docs/protocolo.md` e `docs/estados.md`. Não é
uma negociação bilateral de revanche: o lobby continua FIFO, não reserva o
adversário anterior e não informa ao cliente que esse adversário recusou.

## 7. Limitações conhecidas

- Sem reconexão a uma partida em andamento e sem recuperação após queda do servidor.
- Sem limite de conexões simultâneas nem proteção contra clientes lentos além do descarte quando o socket falha.
- O pareamento é por ordem de chegada; jogar novamente não garante o mesmo
  adversário.
- Se um jogador enviar `JOIN` e o adversário anterior enviar `QUIT`, o
  primeiro permanece no lobby até outro participante entrar ou até encerrar a
  própria conexão.
