# Arquitetura

O sistema tem **um processo servidor** e **dois processos clientes** independentes, ligados por **sockets TCP**. O protocolo de aplicação **TTTP/1** (JSON por linha, UTF-8, LF) é um contrato único em `shared/protocol.py`, usado pelos dois lados. TTTP/1 é um protocolo da **camada de aplicação** que opera sobre TCP; não reimplementa o TCP.

```text
Cliente X ──┐
            ├── TCP ─── Servidor (lobby + estado oficial + regras)
Cliente O ──┘

shared/protocol.py + shared/transport.py  ← usados por cliente e servidor
```

## Componentes

| Componente | Arquivos | Papel |
|---|---|---|
| Protocolo | `shared/protocol.py` | Catálogo, validação sintática, `encode_message`/`decode_message`. Sem rede. |
| Transporte | `shared/transport.py` | `MessageChannel` com buffer por conexão, `listen`/`accept`/`connect` como primitivas. Biblioteca, não processo. |
| Cliente | `client/` | Interface, handshake, lobby, envio de `MOVE`, exibição do estado oficial. |
| Servidor | `server/server.py` | Decide quando aceitar conexões, administra sessões, roteia mensagens. |
| Lobby | `server/lobby.py` | Fila de espera e pareamento. |
| Regras | `server/game.py` | Estado autoritativo e regras puras, testáveis sem sockets. |
| Apresentação | `interface/` | Backends PySide6, telas Qt Quick/QML e espelho textual; observa os módulos reais sem duplicar protocolo ou regras. |
| Telemetria local | `shared/telemetry.py` | Eventos opcionais de aplicação/transporte; nunca entram no payload TTTP/1. |

As aplicações gráficas continuam sendo os mesmos processos cliente e servidor.
Quando um terminal interativo inicia os módulos, `client.client` e
`server.server` carregam as respectivas janelas de `interface/`; com
`--terminal-only`, executam somente o fluxo textual anterior. Detalhes e
critérios visuais: [interface_grafica.md](interface_grafica.md).

A dependência PySide6 existe somente na camada de apresentação. O protocolo,
o transporte, as regras e os processos de cliente/servidor continuam em Python
e preservam os mesmos pontos de entrada e contratos TTTP/1.

## Fluxo nominal

1. Cliente conecta e envia `HELLO`; servidor responde `WELCOME(client_id)`.
2. Cliente envia `JOIN`; sem adversário, recebe `WAITING`.
3. Ao formar o par, o servidor envia `START` (mesmo `game_id`, marcas X/O, `first_turn: "X"`) e `BOARD` (`revision: 0`) aos dois.
4. O jogador do turno envia `MOVE`; o servidor responde `MOVE_RESULT` ao solicitante e `BOARD` aos dois.
5. Se a jogada encerra a partida, ambos recebem `GAME_OVER` depois do `BOARD`.
6. Depois de `GAME_OVER`, o cliente pode enviar novo `JOIN` para voltar ao
   lobby na mesma conexão. O novo pareamento recebe outro `game_id` e pode
   envolver outro adversário.
7. `QUIT`/EOF encerram a sessão; o adversário de uma partida ativa recebe
   `GAME_OVER(ABORTED, OPPONENT_LEFT)`.

Estados e transições: [estados.md](estados.md). Regras do servidor, concorrência e desconexões: [servidor.md](servidor.md). Mensagens e erros: [protocolo.md](protocolo.md).

## Por que TCP

A partida exige entrega ordenada e confiável de poucas mensagens pequenas; TCP garante isso, e o protocolo só precisa delimitar mensagens (LF), porque TCP é um fluxo de bytes sem fronteiras. Detalhes em [transporte.md](transporte.md).

## Testes

`python -m unittest discover -s tests -v` — regras (`test_game.py`), lobby
(`test_lobby.py`), protocolo, transporte, servidor com sockets de loopback
(`test_server.py`) e integração com servidor em processo separado
(`test_integration.py`).

O teste de integração automatizado usa dois canais TCP como participantes; ele
não inicia duas instâncias interativas de `python -m client.client`. A
demonstração final com três processos reais e a captura do Wireshark continuam
como verificações manuais pendentes.
