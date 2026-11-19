# Jogo da Velha Multiplayer (UESC)

Aplicação distribuída de jogo da velha 3×3 em que **dois programas clientes**,
executados em processos independentes, comunicam-se com **um servidor central**
por sockets TCP. Cliente e servidor trocam mensagens do protocolo de aplicação
próprio **TTTP/1**, documentado neste README e implementado em Python.

## Integrantes

- Samuel Ferreira Santos
- Guilherme Crocamo Freire
- Gustavo Souza Silva

Este arquivo é a **documentação principal e autocontida** do projeto. Os
documentos em [`docs/`](docs/) aprofundam decisões de arquitetura, transporte,
cliente, servidor, interface e protocolo sem substituir o contrato resumido
aqui.

## Propósito e funcionamento da aplicação

O objetivo é demonstrar comunicação cliente-servidor, uso direto de sockets
TCP e definição de um protocolo da camada de aplicação. O servidor é a única
autoridade sobre o estado da partida: ele forma os pares, atribui X e O,
controla o turno, valida as jogadas, atualiza o tabuleiro e informa o resultado.

O primeiro cliente entra no lobby e aguarda. Quando o segundo entra, o servidor
cria uma partida, atribui **X ao primeiro jogador e O ao segundo**, e X começa.
Cada cliente envia somente a coordenada desejada; a interface só altera o
tabuleiro depois de receber o snapshot oficial do servidor. Há vitória com
três marcas iguais em uma linha, coluna ou diagonal, e empate quando as nove
casas ficam ocupadas sem vencedor.

Depois de vitória ou empate, uma conexão ainda aberta pode solicitar outra
partida. Esse fluxo, apresentado na interface como “revanche”, retorna o
cliente ao lobby e sempre produz um novo `game_id`; o pareamento FIFO não
garante o mesmo adversário nem a mesma marca.

## Arquitetura

```text
Cliente X ──┐
            ├── TCP ─── Servidor (lobby + estado oficial + regras)
Cliente O ──┘

shared/protocol.py + shared/transport.py
      ├── usados pelo cliente
      └── usados pelo servidor
```

| Componente | Responsabilidade |
|---|---|
| `shared/protocol.py` | Catálogo TTTP/1, validação dos campos e codificação/decodificação JSON. |
| `shared/transport.py` | Socket TCP, enquadramento JSONL, buffer de recepção e envio serializado. |
| `server/server.py` | Escuta, sessões simultâneas, roteamento, ordem das respostas e encerramento. |
| `server/lobby.py` | Fila FIFO, pareamento seguro, atribuição X/O e criação de `game_id`. |
| `server/game.py` | Tabuleiro autoritativo, turnos, validação e resultado da partida. |
| `client/client.py` | Conexão, handshake, lobby, envio de jogadas e processamento das respostas. |
| `interface/` | Janelas PySide6/QML e apresentação do estado recebido; não decide regras. |

O servidor atende conexões concorrentemente. Há proteção do lobby e de cada
partida contra acessos simultâneos, e os envios de uma mesma conexão são
serializados para preservar a ordem das mensagens.

## Por que foi escolhido TCP

O jogo exige que comandos e atualizações cheguem **sem perdas, sem duplicação
e na ordem correta**. TCP oferece um fluxo confiável e ordenado, além de
detectar o encerramento da conexão. Isso permite que o protocolo TTTP/1 se
concentre nas mensagens do jogo, usando LF para delimitar registros, em vez de
implementar retransmissão, ordenação e confirmação sobre UDP.

TCP é um fluxo de bytes, não de mensagens. Por isso, a aplicação mantém um
buffer por conexão: um `recv()` pode trazer parte de uma mensagem ou várias
mensagens juntas. O enquadramento JSONL reconstrói cada registro sem descartar
o restante do buffer.

## Requisitos mínimos de funcionamento

- Python **3.11 ou superior**;
- PySide6 **6.12.0** para as janelas Qt Quick/QML;
- um processo servidor e dois processos clientes;
- conectividade TCP entre os clientes e o endereço/porta do servidor;
- porta TCP 5000 disponível, ou outra porta informada igualmente aos três
  processos;
- em máquinas diferentes, permissão de entrada no firewall do servidor.

A rede, o protocolo e as regras usam somente a biblioteca padrão do Python. A
dependência PySide6 pertence apenas à camada visual.

Instale a dependência visual na raiz do repositório:

```bash
python -m pip install -r requirements.txt
```

## Como executar

### Servidor e clientes na mesma máquina

Abra três terminais PowerShell/CMD na raiz do repositório:

```bash
# Terminal 1 — servidor
python -m server.server --host 127.0.0.1 --port 5000

# Terminal 2 — primeiro cliente
python -m client.client --host 127.0.0.1 --port 5000

# Terminal 3 — segundo cliente
python -m client.client --host 127.0.0.1 --port 5000
```

`127.0.0.1` é o endereço de loopback e só aceita clientes da própria máquina.
Essa demonstração não depende de acesso à Internet.

### Clientes em outras máquinas da mesma rede local

No computador que executará o servidor:

```bash
python -m server.server --host 0.0.0.0 --port 5000
```

Nos clientes, substitua `IP_DO_SERVIDOR` pelo IPv4 local do computador
servidor, obtido no Windows com `ipconfig`:

```bash
python -m client.client --host IP_DO_SERVIDOR --port 5000
```

Os computadores devem estar na mesma LAN, e o firewall do servidor deve
permitir conexões TCP de entrada na porta escolhida em redes privadas. O
endereço `0.0.0.0` é usado apenas para a escuta do servidor; os clientes devem
usar o endereço real do servidor. A conectividade pode ser verificada em outro
Windows, com o servidor já aberto, por:

```powershell
Test-NetConnection IP_DO_SERVIDOR -Port 5000
```

Em redes diferentes, também é necessário tornar o servidor alcançável por
roteamento, redirecionamento de porta ou VPN. Como a versão acadêmica não usa
TLS nem autenticação, recomenda-se uma rede local ou VPN privada em vez de
expor a porta diretamente à Internet.

### Modos de apresentação

Em um terminal interativo, cada módulo abre sua janela gráfica e mantém no
terminal um espelho textual dos mesmos estados e mensagens. As opções abaixo
permitem escolher explicitamente a apresentação:

```bash
# Somente a interface textual
python -m server.server --terminal-only
python -m client.client --terminal-only

# Força a janela mesmo fora de um terminal interativo
python -m server.server --gui
python -m client.client --gui
```

As janelas mostram a passagem real por **aplicação → `shared.transport` → TCP
→ aplicação**, incluindo o objeto TTTP/1, bytes, framing JSONL/LF, buffer
residual e decisão da camada de aplicação. Essa telemetria é local e não
acrescenta campos às mensagens de rede.

## Protocolo da camada de aplicação — TTTP/1

TTTP/1 é o contrato comum entre cliente e servidor e opera **sobre TCP**. Não é
uma implementação do próprio TCP.

### Formato e enquadramento

- cada mensagem é um objeto JSON codificado em UTF-8 e terminado por LF
  (`\n`), no formato JSONL;
- todas as mensagens possuem `"type"` em maiúsculas e `"version": 1`;
- o limite é de **4096 bytes por mensagem, incluindo o LF**;
- o receptor mantém um buffer por conexão para tratar fragmentação e
  concatenação de registros;
- o envio usa `sendall()` e é serializado por conexão para evitar intercalação
  de bytes;
- `recv()` retornando `b''` representa EOF, ou seja, fim da conexão;
- nomes de campos e enumerações diferenciam maiúsculas de minúsculas;
- o cliente nunca escolhe sua marca, o próximo turno ou o vencedor.

Exemplo de mensagem completa no fio:

```json
{"type":"MOVE","version":1,"game_id":"g17","row":1,"col":2}
```

Após o `}`, há um byte LF que delimita o registro.

### Catálogo completo de mensagens

Os campos `type` e `version` são obrigatórios em todas as linhas. A coluna
“payload” lista os demais campos.

| Mensagem | Direção | Payload | Função |
|---|---|---|---|
| `HELLO` | Cliente → servidor | — | Iniciar o handshake TTTP/1. |
| `WELCOME` | Servidor → cliente | `client_id` | Confirmar o handshake e identificar a sessão. |
| `JOIN` | Cliente → servidor | — | Entrar no lobby, inclusive após uma partida encerrada. |
| `WAITING` | Servidor → cliente | — | Informar que ainda falta um adversário. |
| `START` | Servidor → cliente | `game_id`, `mark`, `first_turn` | Informar a partida, a marca X/O e que X começa. |
| `MOVE` | Cliente → servidor | `game_id`, `row`, `col` | Solicitar jogada com índices inteiros de 0 a 2. |
| `MOVE_RESULT` aceito | Servidor → solicitante | `game_id`, `status="ACCEPTED"`, `row`, `col`, `revision` | Confirmar a jogada aceita. |
| `MOVE_RESULT` rejeitado | Servidor → solicitante | `game_id`, `status="REJECTED"`, `code`, `message` | Rejeitar semanticamente uma jogada sem alterar o estado. |
| `BOARD` | Servidor → ambos | `game_id`, `board`, `turn`, `revision` | Publicar o snapshot oficial da matriz 3×3. |
| `GAME_OVER` | Servidor → ambos | `game_id`, `result`, `winner`; `reason` no aborto | Informar vitória, empate ou interrupção. |
| `ERROR` | Servidor → cliente | `code`, `message` | Informar erro de formato, protocolo ou estado da sessão. |
| `PING` | Qualquer ponta | — | Verificar atividade da conexão; extensão opcional implementada. |
| `PONG` | Resposta ao `PING` | — | Responder ao heartbeat. |
| `QUIT` | Cliente → servidor | — | Encerrar a sessão de forma controlada. |

Em `BOARD`, cada célula contém `"X"`, `"O"` ou `""`. `revision` começa em 0
e aumenta exatamente uma vez por jogada aceita. Depois de vitória, empate ou
aborto, `turn` é `null`.

Na interface textual, o jogador escolhe linha e coluna de **1 a 3**. O cliente
converte essa entrada para os índices **0 a 2** enviados em `MOVE`.

### Ordem dos eventos

1. O cliente abre o socket TCP e envia `HELLO`.
2. O servidor valida a versão e responde `WELCOME(client_id)`.
3. O cliente envia `JOIN`.
4. Sem adversário, recebe `WAITING`; com dois participantes, o servidor forma
   a partida.
5. Ambos recebem `START` com o mesmo `game_id`, marcas diferentes e
   `first_turn: "X"`.
6. Ambos recebem o `BOARD` inicial, vazio e com `revision: 0`.
7. Somente o participante do turno envia `MOVE`.
8. Em uma jogada aceita, o solicitante recebe `MOVE_RESULT(ACCEPTED)` e depois
   ambos recebem o novo `BOARD`.
9. Se a jogada encerrar a partida, ambos recebem `GAME_OVER` depois do
   `BOARD` terminal.
10. Em uma jogada inválida, somente o solicitante recebe
    `MOVE_RESULT(REJECTED)`; tabuleiro, turno e revisão não mudam.
11. `QUIT`, EOF ou falha de socket encerram a sessão. Se havia uma partida
    ativa, o adversário recebe `GAME_OVER(ABORTED, OPPONENT_LEFT)` quando o
    envio ainda é possível.
12. Depois de `GAME_OVER`, o cliente pode enviar `JOIN` para voltar ao lobby ou
    `QUIT` para encerrar a conexão.

Em uma jogada terminal aceita, a ordem observável é sempre:
`MOVE_RESULT` → `BOARD` → `GAME_OVER`.

### Estados da sessão

```text
DESCONECTADO
   │ conectar TCP
   ▼
CONECTADO ── HELLO/WELCOME ──▶ IDENTIFICADO
                                  │ JOIN
                                  ▼
                              AGUARDANDO
                                  │ START + BOARD
                                  ▼
                              EM_PARTIDA
                                  │ GAME_OVER
                                  ▼
                              ENCERRADO
                                  ├── JOIN ──▶ AGUARDANDO (nova partida)
                                  └── QUIT/EOF ──▶ DESCONECTADO
```

Qualquer estado conectado pode ir para `DESCONECTADO` por EOF ou falha de
socket. Comandos incompatíveis com o estado atual recebem erro sem alterar a
partida.

### Estados da partida

```text
ATIVA ── jogada aceita sem resultado ──▶ ATIVA (turno alterna, revision + 1)
ATIVA ── vitória ou empate ────────────▶ FINALIZADA (turn = null)
ATIVA ── QUIT/EOF de um jogador ──────▶ ABORTADA   (turn = null)
```

`FINALIZADA` e `ABORTADA` são estados terminais. Nenhuma jogada posterior
altera a partida encerrada.

### Erros e rejeições

| Código | Situação | Tratamento |
|---|---|---|
| `BAD_FORMAT` | UTF-8/JSON inválido, campo ausente, inesperado ou com tipo errado. | `ERROR`; partida não muda. |
| `UNKNOWN_TYPE` | `type` não pertence ao catálogo. | `ERROR`; partida não muda. |
| `UNSUPPORTED_VERSION` | `version` diferente de 1. | `ERROR` e fechamento controlado. |
| `MESSAGE_TOO_LARGE` | Registro excede 4096 bytes. | `ERROR` quando possível e fechamento. |
| `INVALID_STATE` | Comando incompatível com o estado da sessão. | `ERROR`; sem mutação indevida. |
| `NOT_IN_GAME` | `MOVE` sem partida ativa ou com `game_id` alheio. | `MOVE_RESULT(REJECTED)`. |
| `NOT_YOUR_TURN` | Jogador tenta agir fora do turno. | `MOVE_RESULT(REJECTED)`. |
| `INVALID_POSITION` | Linha ou coluna fora de 0..2. | `MOVE_RESULT(REJECTED)`. |
| `OCCUPIED` | A célula já está ocupada. | `MOVE_RESULT(REJECTED)`. |
| `GAME_FINISHED` | Jogada depois do encerramento. | `MOVE_RESULT(REJECTED)`. |
| `TIMEOUT` | Tempo de conexão/handshake excedido. | Evento local; pode não ser possível responder. |

Problemas de formato, protocolo ou estado da sessão usam `ERROR`. Rejeições
semânticas de um `MOVE` bem formado usam somente `MOVE_RESULT(REJECTED)`. O
servidor não envia as duas respostas para a mesma falha, e uma rejeição nunca
altera célula, turno, revisão, vencedor ou estado.

## Regras e invariantes da partida

- cada partida possui exatamente dois participantes distintos, X e O;
- X sempre faz a primeira jogada;
- `row` e `col` são inteiros de 0 a 2 e valores booleanos não são aceitos;
- somente o servidor atribui marcas e mantém o tabuleiro oficial;
- uma jogada aceita ocupa uma célula vazia e incrementa `revision` uma vez;
- uma jogada inválida não produz efeitos colaterais;
- após jogada aceita, são verificadas 3 linhas, 3 colunas e 2 diagonais;
- vitória tem precedência sobre empate;
- snapshots enviados aos dois jogadores têm o mesmo `game_id`, tabuleiro e
  revisão;
- o cliente nunca usa seu próprio cálculo como fonte oficial do resultado.

## Desconexões e nova partida

- saída no lobby remove a sessão da fila;
- saída durante uma partida aborta o jogo e informa `OPPONENT_LEFT` ao
  adversário quando possível;
- abandono não conta como vitória;
- não há recuperação de uma partida depois da desconexão;
- um novo `JOIN` na mesma conexão inicia outro pareamento e não reabre o
  `game_id` anterior;
- queda do servidor encerra as conexões; os clientes exibem a falha localmente.

## Estrutura do repositório

```text
shared/       protocolo TTTP/1, transporte TCP e telemetria local
client/       sessão e fluxo do cliente
server/       servidor, lobby e regras autoritativas
interface/    janelas PySide6/QML
tests/        testes unitários e de integração
tools/        gerador reproduzível de tráfego TTTP/1
docs/         documentação técnica detalhada
```

## Testes e verificação

Execute toda a suíte a partir da raiz:

```bash
python -m unittest discover -s tests -v
```

A suíte contém 152 testes para regras, lobby, protocolo, framing TCP,
fragmentação e concatenação, Unicode, limites de tamanho, concorrência,
desconexões, cliente, servidor, interface e integração. O teste de integração
abre o servidor em processo separado e usa dois participantes TCP para concluir
uma partida.

Como evidência manual final, ainda se recomenda executar as duas instâncias
interativas do cliente, registrar as telas e salvar uma captura `.pcapng` do
tráfego TTTP/1. O gerador e o procedimento estão descritos em
[`docs/transporte.md`](docs/transporte.md#10-inspeção-no-wireshark--t12).

## Documentação técnica detalhada

Este README contém a documentação exigida para compreender e executar a
aplicação. Os arquivos abaixo preservam justificativas, esquemas e critérios de
teste com maior profundidade:

- [Arquitetura e componentes](docs/arquitetura.md)
- [Contrato normativo do protocolo TTTP/1](docs/protocolo.md)
- [Transporte TCP, framing e Wireshark](docs/transporte.md)
- [Fluxo e comportamento do cliente](docs/cliente.md)
- [Servidor, concorrência e desconexões](docs/servidor.md)
- [Máquinas de estados](docs/estados.md)
- [Interface gráfica e observabilidade](docs/interface_grafica.md)
- [Declaração de uso de inteligência artificial](docs/declaracao_uso_ia.md)
- [Linha do tempo de modificações](docs/linha_do_tempo.md)
