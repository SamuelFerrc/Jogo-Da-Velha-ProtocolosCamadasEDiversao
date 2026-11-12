# AGENTS.md — Jogo da Velha Multiplayer (UESC)

> Instruções de desenvolvimento para agentes de código e integrantes da equipe.
> Projeto acadêmico de comunicação cliente-servidor com **sockets TCP** e **protocolo próprio de aplicação**.
> **Este projeto é JOGO DA VELHA (tabuleiro 3×3), não Batalha Naval.** Não introduza navios, ataques, posicionamento de peças ou regras de outro jogo.

## 1. Objetivo e escopo

Implementar um sistema distribuído em que **dois programas clientes**, executados em processos distintos, disputam uma partida de jogo da velha conectados a **um servidor central** por TCP. O servidor é a única autoridade sobre o estado da partida. A aplicação deve evidenciar o domínio da camada de transporte e a criação/documentação de um protocolo da camada de aplicação.

### Requisitos mínimos obrigatórios

- Pelo menos um processo servidor e dois processos clientes independentes.
- Comunicação efetiva por **sockets TCP**, sem HTTP, WebSocket, REST ou serviços externos como mecanismo principal do jogo.
- Mensagens de aplicação próprias, especificadas e testadas (TTTP/1, detalhado abaixo).
- Tabuleiro **3×3**; jogadores **X** e **O**; **X começa**; turnos alternados.
- Validação no servidor de turno, participação, índice de linha/coluna, célula vazia e término.
- Vitória por três marcas iguais em linha, coluna ou diagonal; empate com nove casas ocupadas e nenhum vencedor.
- Tratamento de conexões interrompidas, mensagens inválidas e concorrência entre clientes.
- Documentação de arquitetura, protocolo de aplicação, máquina de estados, eventos, requisitos de execução e testes.

**Fora do escopo mínimo:** autenticação complexa, persistência de contas, placar histórico, reconexão de partida, chat, IA adversária, matchmaking sofisticado e interface gráfica obrigatória. Não implemente extensões antes de concluir os testes essenciais.

## 2. Fontes e precedência de decisões

As referências do planejamento são:

1. `Projeto_Jogo_da_Velha_Cliente_Servidor_UESC_ABNT.pdf` — arquitetura, requisitos, mensagens e diagramas.
2. `Plano_Etapas_Jogo_da_Velha_UESC.xlsx` — tarefas **T01–T13**, **C01–C13**, **S01–S15** e marcos **I01–I08**.
3. **Este `AGENTS.md`** — regras executáveis de organização, contratos concretos da versão 1, verificações e resolução das ambiguidades encontradas.

Quando houver diferença entre um exemplo **ilustrativo** do PDF e o contrato concreto da seção 5, implemente o contrato concreto **e registre a divergência para harmonização do PDF/planilha**. Nunca altere silenciosamente um tipo de mensagem, campo, estado ou código de erro só em um lado. Mudanças deliberadas de protocolo exigem atualização conjunta de `shared/protocol.py`, `docs/protocolo.md`, testes e clientes/servidor envolvidos. A versão 1 não deve sofrer alterações incompatíveis sem uma decisão explícita da equipe.

### Inspeção inicial obrigatória para qualquer agente

1. Examine os arquivos reais antes de criar ou editar código; não presuma que módulos já existem.
2. Identifique qual frente está alterando: Transporte, Cliente ou Servidor.
3. Confira `docs/protocolo.md` e a API de `shared/` antes de usar mensagens ou funções.
4. Declare o comportamento esperado, os testes de aceitação e impactos nos outros módulos.
5. Após cada mudança, rode os testes pertinentes e apresente o que foi verificado e o que não foi possível executar.
6. Antes de encerrar, registre a mudança em `docs/linha_do_tempo.md` conforme a seção 14 deste arquivo.

## 3. Arquitetura e limites entre as três partes

```text
Cliente X ──┐
            ├── TCP ─── Servidor (lobby + estado oficial + regras)
Cliente O ──┘

shared/protocol.py + shared/transport.py
      ├── usados pelo Cliente
      └── usados pelo Servidor
```

**Importante:** a frente de **Transporte** é uma **biblioteca compartilhada**, não um terceiro processo de rede, proxy, intermediário ou servidor separado. O **protocolo de aplicação é um único contrato comum** para os dois lados; o cliente o usa para solicitar e interpretar, e o servidor para validar e responder.

| Frente | Responsabilidade exclusiva/principal | Não deve fazer |
|---|---|---|
| **1. Transporte e protocolo** | Utilizar sockets TCP; UTF-8; JSON por linha; serializar, enquadrar, receber, validar estrutura; erros de rede; definir contrato comum. | Decidir vencedores, alterar tabuleiro, atribuir turnos ou desenhar interface. |
| **2. Cliente** | Interface 3×3; leitura de jogadas; handshake; lobby; exibição de estado e notificações; envio de comandos via `shared/`. | Criar a verdade oficial do jogo ou assumir que uma jogada foi aceita antes do servidor. |
| **3. Servidor** | Aceitar conexões; criar sessões; parear jogadores; manter partidas; validar/aplicar jogadas; sincronizar clientes; encerrar partidas. | Depender da interface ou confiar em `mark`/`turn` informados pelo cliente. |

**Separação específica dos sockets:** `shared/transport.py` pode disponibilizar funções auxiliares de baixo nível para conectar, escutar, aceitar, enviar e receber. A **decisão de quando aceitar conexões e como administrar clientes pertence a `server/server.py`**; a decisão de quando se conectar pertence a `client/client.py`. Não mantenha dois algoritmos concorrentes de enquadramento ou serialização.

## 4. Estrutura prevista do repositório

Crie apenas os arquivos ainda inexistentes e adapte os nomes se o repositório já possuir uma organização equivalente; preserve a separação de responsabilidades.

```text
jogo-da-velha/
├── AGENTS.md
├── README.md
├── shared/
│   ├── __init__.py
│   ├── protocol.py          # Catálogo, versão, estruturas e validação sintática
│   └── transport.py         # Socket TCP, JSONL, buffer, envio/recepção, fechamento
├── client/
│   ├── __init__.py
│   ├── client.py            # Sessão, envio de ações e processamento de mensagens
│   └── interface.py         # Tabuleiro 3×3, entrada e mensagens para usuário
├── server/
│   ├── __init__.py
│   ├── server.py            # Escuta, atendimento simultâneo, sessões, ciclo de vida
│   ├── lobby.py             # Fila de espera e pareamento de jogadores
│   └── game.py              # Estado autoritativo e regras puras da partida
├── tests/
│   ├── test_protocol.py
│   ├── test_transport.py
│   ├── test_client.py
│   ├── test_game.py
│   ├── test_server.py
│   └── test_integration.py
└── docs/
    ├── protocolo.md        # Contrato normativo dos tipos/campos/erros
    ├── transporte.md       # TCP, framing, EOF, timeout e limites
    ├── cliente.md          # Operação e estados do cliente
    ├── servidor.md         # Operação e regras do servidor
    ├── estados.md          # Máquinas de estados e transições
    └── arquitetura.md      # Componentes, sequência, requisitos e diagramas
```

Os nomes de `docs/` podem manter equivalentes já adotados, desde que não existam documentos contraditórios. `README.md` precisa indicar como iniciar um servidor e dois clientes a partir da raiz do repositório.

## 5. Contrato único do protocolo de aplicação — TTTP/1

**TTTP/1** é o nome de trabalho indicado no PDF para o protocolo didático. Apesar de conter a palavra *Transport* no nome expandido, **é um protocolo da camada de aplicação**, que opera **sobre TCP**. **Não** confundir o protocolo próprio com uma implementação do TCP.

### 5.1 Formato e enquadramento

- Cada mensagem é **um objeto JSON**, codificado em **UTF-8**, terminado por **LF (`\n`)**: formato JSONL / JSON por linha.
- Campos obrigatórios em **todas** as mensagens: `"type"` (string maiúscula) e `"version": 1` (inteiro). Os exemplos reduzidos do PDF não dispensam `version`.
- Tamanho máximo de **4096 bytes por mensagem, incluindo LF**, adotado como decisão operacional da v1. Registrar esse limite em `docs/protocolo.md` e nos testes.
- `recv()` retorna blocos de **bytes**, não mensagens completas. Manter **buffer de recepção por conexão** para reconstruir mensagens fragmentadas e separar mensagens concatenadas.
- Não consumir bytes além de um delimitador descartando o restante do buffer; uma única leitura pode conter várias mensagens.
- Uma string JSON que contenha quebra de linha deve conter a forma escapada `\n`, não um LF literal no meio do registro.
- Envio por `sendall()` (ou mecanismo equivalente), com **serialização dos envios por conexão** para evitar intercalar bytes de threads diferentes.
- O fechamento de `recv()` com resultado `b''` indica fim do fluxo, não uma mensagem de aplicação vazia.
- `type`, nomes de campos, valores de enumeração e índices têm grafia **exata** e diferenciada por maiúsculas/minúsculas.
- **Nenhum** cliente determina sua própria marca, vencedor ou próximo turno via `MOVE`.

### 5.2 Esquema canônico de mensagens

Os objetos abaixo são exemplos **completos da v1**. Os campos entre chaves fornecidos pelo sistema devem ser considerados variáveis de execução, não constantes literais.

**Cliente → Servidor**

```json
{"type":"HELLO","version":1}
{"type":"JOIN","version":1}
{"type":"MOVE","version":1,"game_id":"g17","row":1,"col":2}
{"type":"QUIT","version":1}
```

**Servidor → Cliente(s)**

```json
{"type":"WELCOME","version":1,"client_id":"c42"}
{"type":"WAITING","version":1}
{"type":"START","version":1,"game_id":"g17","mark":"X","first_turn":"X"}
{"type":"BOARD","version":1,"game_id":"g17","board":[["","",""],["","",""],["","",""]],"turn":"X","revision":0}
{"type":"MOVE_RESULT","version":1,"game_id":"g17","status":"ACCEPTED","row":1,"col":2,"revision":1}
{"type":"MOVE_RESULT","version":1,"game_id":"g17","status":"REJECTED","code":"OCCUPIED","message":"Posição já ocupada"}
{"type":"GAME_OVER","version":1,"game_id":"g17","result":"WIN","winner":"X"}
{"type":"GAME_OVER","version":1,"game_id":"g17","result":"DRAW","winner":null}
{"type":"GAME_OVER","version":1,"game_id":"g17","result":"ABORTED","winner":null,"reason":"OPPONENT_LEFT"}
{"type":"ERROR","version":1,"code":"BAD_FORMAT","message":"Mensagem inválida"}
```

As mensagens de tabuleiro (`BOARD`) usam **matriz 3×3**; cada célula contém `"X"`, `"O"` ou `""` (vazia). `row` e `col` variam de **0 a 2** (inteiros, **não** booleanos), com `[0][0]` no canto superior esquerdo. `revision` começa em `0` e aumenta **exatamente uma vez por jogada aceita**, para que os clientes possam identificar snapshots antigos. Quando a partida termina, o campo `turn` de `BOARD` é `null`.

**PING/PONG são opcionais**. Se implementados, usar `{"type":"PING","version":1}` e `{"type":"PONG","version":1}`. Não tornar essas mensagens obrigatórias na primeira entrega.

### 5.3 Ordem nominal de eventos (obrigatória)

1. Cliente abre socket TCP e envia `HELLO`.
2. Servidor valida a versão e retorna `WELCOME` com `client_id`.
3. Cliente envia `JOIN`.
4. Se não houver adversário, servidor envia `WAITING`; quando houver dois participantes, forma a partida.
5. Servidor envia `START` para **ambos**, com **mesmo `game_id`**, marcas diferentes (`X` e `O`) e `first_turn: "X"`.
6. Servidor envia `BOARD` inicial (`revision: 0`) aos dois.
7. Somente jogador do turno envia `MOVE`; servidor valida e aplica **uma única vez**.
8. Em jogada aceita: servidor envia `MOVE_RESULT(status=ACCEPTED)` **ao solicitante**, depois `BOARD` atualizado **aos dois**.
9. Se a jogada encerrou a partida: após `BOARD`, servidor envia `GAME_OVER` **aos dois**.
10. Em jogada inválida: enviar **somente** `MOVE_RESULT(status=REJECTED, code=...)` ao solicitante; **não** incrementar `revision` nem alterar tabuleiro/turno.
11. `QUIT`, EOF ou falha de conexão encerram a sessão; se havia adversário em partida, avisar o adversário por `GAME_OVER(result=ABORTED, reason=OPPONENT_LEFT)`.

**Regra de compatibilidade adotada:** para rejeições semânticas de `MOVE`, usar `MOVE_RESULT` com `status=REJECTED`. Reservar `ERROR` para problemas de formato, protocolo ou estado de sessão fora de uma jogada bem formada. O PDF traz um exemplo ilustrativo `ERROR` com `OCCUPIED`; essa divergência precisa ser corrigida na documentação formal, e **não** implementada como dois comportamentos alternativos. Não enviar `ERROR` *e* `MOVE_RESULT` para a mesma rejeição.

### 5.4 Erros e destino de cada um

| Código | Quando ocorre | Resposta/efeito |
|---|---|---|
| `BAD_FORMAT` | UTF-8/JSON inválido; campos obrigatórios ausentes ou de tipo incorreto | `ERROR`; não modificar partida. |
| `UNKNOWN_TYPE` | `type` desconhecido | `ERROR`; não modificar partida. |
| `UNSUPPORTED_VERSION` | `version` diferente de 1 | `ERROR`, seguido de fechamento controlado. |
| `MESSAGE_TOO_LARGE` | Registro excede 4096 bytes | `ERROR` se possível e fechar conexão. |
| `INVALID_STATE` | `JOIN`/`HELLO` fora da fase permitida | `ERROR`; manter ou encerrar sessão conforme gravidade. |
| `NOT_IN_GAME` | `MOVE` sem participação em partida ativa ou `game_id` alheio | `MOVE_RESULT(REJECTED)`; sem mutação. |
| `NOT_YOUR_TURN` | `MOVE` recebido do jogador errado | `MOVE_RESULT(REJECTED)`; sem mutação. |
| `INVALID_POSITION` | Índices fora de 0..2 | `MOVE_RESULT(REJECTED)`; sem mutação. |
| `OCCUPIED` | Célula contém X ou O | `MOVE_RESULT(REJECTED)`; sem mutação. |
| `GAME_FINISHED` | `MOVE` depois do encerramento da partida | `MOVE_RESULT(REJECTED)`; sem mutação. |
| `TIMEOUT` | Conexão/espera expirada por política local | Evento local de transporte/sessão; **não presumir** que seja possível responder na rede. |

`message` é texto para apresentação/log; a aplicação deve decidir comportamento pelo **código**, nunca comparando frases. Não incluir detalhes de exceções internas do servidor no campo `message`.

### 5.5 Política de sessão e desconexões

- Nesta versão, **não há recuperação de partida após a desconexão**. Pode-se iniciar uma nova sessão/partida a partir de nova conexão; não há reentrada automática em `game_id` antigo.
- `QUIT` fecha a sessão depois de o servidor processar a saída; não exigir `BYE`, que não faz parte do catálogo.
- Se alguém abandonar o lobby, retirar sua sessão da fila; não formar partida com clientes desconectados.
- Se um participante abandonar partida ativa, marcar o jogo como abortado e notificar o outro com `GAME_OVER(ABORTED)`. **Abandono não conta automaticamente como vitória** nesta versão.
- Timeout de **conexão/handshake** pode ser parametrizado; não aplicar timeout curto ao tempo de reflexão de uma jogada. Heartbeat de aplicação só se a extensão PING/PONG for realmente aprovada e testada.
- Falha na tentativa de notificar um socket já fechado é tratada localmente e não deve provocar corrupção de partida.

## 6. Máquinas de estados e invariantes

### 6.1 Estado da sessão do cliente

```text
DESCONECTADO
   │ conectar TCP
   ▼
CONECTADO
   │ HELLO → WELCOME
   ▼
IDENTIFICADO
   │ JOIN → WAITING
   ▼
AGUARDANDO
   │ START (+ BOARD inicial)
   ▼
EM_PARTIDA
   │ GAME_OVER
   ▼
ENCERRADO
   │ QUIT / encerramento TCP
   ▼
DESCONECTADO
```

**Qualquer** estado conectado pode passar a `DESCONECTADO` em EOF/falha. `WAITING` só existe após `JOIN`. O servidor também possui um estado **interno da partida** (`AGUARDANDO`, `ATIVA`, `FINALIZADA` ou `ABORTADA`), distinto do estado de sessão TCP. Não tratar os estados como mensagens da camada de transporte.

### 6.2 Invariantes de jogo (nunca violar)

- Uma partida tem **exatamente dois participantes distintos**, um X e um O.
- A marca de um cliente é definida **pelo servidor** no `START`.
- Tabuleiro é uma matriz **3×3** e nunca tem outras marcas.
- X faz a primeira jogada; após movimento válido não terminal, turno alterna; após terminal, `turn = null`.
- Jogada inválida é **sem efeitos colaterais**: não modifica células, turno, `revision`, vencedor ou estado.
- Após vitória/empate/aborto, nenhuma jogada altera a partida.
- `GAME_OVER` só ocorre com estado final consistente; não emitir vitória e empate simultaneamente.
- Todos os clientes da mesma partida recebem snapshots com o **mesmo** `game_id`, tabuleiro e `revision`.
- O cliente **nunca** utiliza seu próprio cálculo de vitória como fonte de verdade.

### 6.3 Verificação de resultado

Analisar, após **cada jogada aceita**, as **3 linhas**, **3 colunas** e **2 diagonais**. Há `WIN` quando uma das oito combinações possui três marcas iguais não vazias. Há `DRAW` apenas se não houve `WIN` e as nove células estão ocupadas. Caso contrário, continuar com o próximo turno.

## 7. Concorrência, robustez e segurança mínima

- O servidor precisa atender **pelo menos dois sockets ao mesmo tempo** (threads ou `asyncio`); nunca bloquear o segundo cliente enquanto aguarda `MOVE` do primeiro.
- Utilizar **lock por partida** (ou serialização de eventos equivalente) para validar + aplicar uma jogada + gerar snapshot de forma **atômica**.
- Proteger o pareamento do lobby e a alteração do estado das sessões com locks ou fila única de eventos.
- Serializar **todos os envios de uma mesma conexão**; `sendall()` não garante, isoladamente, que duas threads não intercalem seus registros.
- Não manter lock de partida durante operações de rede que possam bloquear; gerar snapshots/resultados sob lock e enfileirar o envio em ordem após liberar o lock.
- Preservar a **ordem lógica de mensagens de uma partida** por conexão, inclusive `MOVE_RESULT`, `BOARD` e `GAME_OVER`.
- Em erros de parsing, rejeitar a entrada sem executar comandos. Nunca usar `eval()` ou desserialização insegura.
- Validar comprimento antes de acumular buffers sem limite. Não aceitar coordenadas booleanas (em Python, `bool` é subtipo de `int`), números fracionários nem listas no lugar de `row`/`col`.
- Não confiar em `client_id`, `mark`, `turn` ou `winner` recebidos do cliente para autenticar ações.
- Registrar eventos sem depender da interface: conexão, pareamento, mensagem inválida, jogada aceita/rejeitada, término, EOF e exceções.
- Configurar host/porta por parâmetros ou configuração. Para testes locais, preferir `127.0.0.1`; ouvir em interfaces externas só quando necessário.

## 8. APIs esperadas e responsabilidade de cada arquivo

### 8.1 `shared/protocol.py` — sem acesso à rede

Implementar ou expor funções equivalentes a:

```python
PROTOCOL_VERSION = 1
MAX_MESSAGE_BYTES = 4096

# Assinaturas de referência, não implementações prontas:
def validate_envelope(message: dict) -> None: ...
def validate_payload(message: dict) -> None: ...
def encode_message(message: dict) -> bytes: ...
def decode_message(data: bytes) -> dict: ...
```

Semântica de `validate_payload`: conferir **campos, enums e tipos**, não decidir turno, ocupação ou vencedor. `encode_message` deve produzir **exatamente um JSON válido + LF**; `decode_message` recebe o conteúdo de **um** registro delimitado.

### 8.2 `shared/transport.py` — sem regras do jogo

Disponibilizar uma abstração de conexão com buffer persistente por socket:

```python
class MessageChannel:
    def send_message(self, payload: dict) -> None: ...
    def receive_message(self) -> dict: ...
    def close(self) -> None: ...
```

Se oferecer `send_message(socket, payload)` e `receive_message(socket)` como wrappers públicos, **não perder o buffer residual** entre chamadas. Documentar exceções próprias ou padronizadas para `EOF`, `Timeout`, tamanho excessivo e falhas de socket.

### 8.3 `client/`

- `client.py`: configuração de endereço/porta, conexão, `HELLO`, `JOIN`, envio de `MOVE`, recebimento contínuo, modelo de estado **de apresentação** e encerramento.
- `interface.py`: imprimir/desenhar tabuleiro e mensagens de estado; capturar coordenadas; evitar travar a leitura da rede enquanto solicita entrada. Interface de terminal é suficiente.
- Mostrar X/O apenas após `START`, e atualizar células apenas depois do `BOARD` oficial. O cliente deve exibir erros `REJECTED` sem alterar a cópia do tabuleiro.

### 8.4 `server/`

- `server.py`: `listen`, `accept`, leitura/roteamento, ciclo de vida e concorrência de sessões.
- `lobby.py`: fila de espera, remoção de desconectados, pareamento seguro, atribuição X/O e `game_id` único.
- `game.py`: estado imutável ou protegido e funções de validação, aplicação, vitória e empate testáveis **sem abrir sockets**.
- Separar erros de payload/protocolo dos erros de jogada e do mecanismo de conexão.

## 9. Etapas de execução alinhadas à planilha

Desenvolver pelas dependências abaixo. As pessoas podem trabalhar em paralelo usando **mocks/stubs** desde que respeitem o contrato congelado em I01.

| Fase | Transporte | Cliente | Servidor | Marco verificável |
|---|---|---|---|---|
| **0 — Contrato** | T01–T03 | C01 (fluxo) | S01 (estados) | **I01**: catálogos e esquemas aprovados por todos. |
| **1 — Base** | T04–T08 | C02–C04 | S02–S03 | **I02**: duas pontas trocam várias mensagens sem confundir registros. |
| **2 — Lobby** | API comum estável | C05–C06 | S04–S06 | **I03**: dois clientes recebem o mesmo `game_id`, X/O distintos e BOARD inicial. |
| **3 — Partida** | Suporte ao tráfego real | C07–C10 | S07–S11 | **I04–I05**: jogadas, sincronização, vitórias X/O e empate. |
| **4 — Robustez** | T09–T11 (+ T10 opcional) | C11–C12 | S12–S14 | **I06–I07**: entradas erradas, quedas, disputa de turnos e nenhum estado inválido. |
| **5 — Evidências** | T12–T13 | C13 | S15 | **I08**: Wireshark, testes, instruções e documentação em acordo com a implementação. |

**Nota de dependência:** a planilha apresenta uma aparente circularidade entre o contrato preliminar e as definições de fluxo/estado. Resolva-a com **rascunho colaborativo** de T01–T03, C01 e S01, seguido da **aprovação única I01**. **Nenhuma implementação dependente do protocolo começa antes de I01**. Depois disso, os módulos avançam em paralelo com simulações.

## 10. Estratégia de testes e comandos

### 10.1 Comandos recomendados

Usar Python **3.11+** e preferir biblioteca padrão (`socket`, `json`, `threading` ou `asyncio`, `unittest`). Não adicionar dependências externas sem necessidade comprovada.

```bash
# Na raiz do repositório:
python -m server.server --host 127.0.0.1 --port 5000
python -m client.client --host 127.0.0.1 --port 5000
python -m client.client --host 127.0.0.1 --port 5000

# Testes automatizados:
python -m unittest discover -s tests -v
```

Esses são os **comandos-alvo** a implementar e documentar no README, **não** uma declaração de que os arquivos executáveis já existem.

### 10.2 Matriz mínima de aceitação

**Transporte/protocolo:** `HELLO/WELCOME`; JSON com Unicode; envio/recepção de vários registros; uma mensagem fragmentada entre `recv()`; duas mensagens em um mesmo `recv()`; registro acima do limite; UTF-8/JSON malformado; versão não suportada; EOF; envio em threads sem intercalar bytes.

**Cliente:** mostra tabuleiro vazio e X/O; digitação de coordenadas 0..2; não antecipa jogadas; recebe jogada do adversário sem depender de novo input; mostra erro sem mudar casa; exibe vitória/empate/aborto; lida com servidor desligado.

**Servidor:** valida marcas/turnos/células; não altera estado em rejeição; forma um único par para cada jogador; não forma partida com desconectado; trata múltiplos MOVE simultâneos; encerra após vitória/empate; limpa lobby e sessões.

**Cenários exatos de regras** (coordenadas no formato `(linha,coluna)`; ordem cronológica, X inicia):

- Vitória de **X**: X(0,0), O(1,0), X(0,1), O(1,1), X(0,2).
- Vitória de **O**: X(0,0), O(1,0), X(0,1), O(1,1), X(2,2), O(1,2).
- **Empate**: X(0,0), O(0,1), X(0,2), O(1,1), X(1,0), O(1,2), X(2,1), O(2,0), X(2,2).
- Rejeição: X tenta duas jogadas consecutivas; O tenta fora do turno; célula ocupada; índice -1 ou 3; tipo errado; `game_id` alheio; MOVE após GAME_OVER.
- Concorrência: duas requisições concorrentes não resultam em duas alterações no mesmo turno; revisões são monotônicas e consistentes.
- Desconexão: cliente sai em `AGUARDANDO`; cliente sai em `EM_PARTIDA`; servidor cai; adversário recebe `ABORTED` quando o envio ainda é possível.

Para integração, usar sockets de loopback em testes automatizados e, na demonstração final, **dois terminais/processos clientes** conectados a um servidor. Registrar, se disponível, captura do Wireshark mostrando TCP e payload JSONL.

## 11. Checklist de consistência antes de cada merge/entrega

- [ ] O projeto continua sendo **Jogo da Velha 3×3**, sem referências acidentais a Batalha Naval.
- [ ] Cliente e servidor importam o **mesmo** `shared/protocol.py` e usam o mesmo esquema TTTP/1.
- [ ] Todos os tipos de mensagem e campos obrigatórios estão documentados e testados.
- [ ] `type` e `version=1` estão presentes em todas as mensagens enviadas.
- [ ] Toda mensagem tem LF, limite de tamanho e buffer por conexão; o parser suporta fragmentação/concatenação.
- [ ] O servidor, e somente ele, controla `game_id`, X/O, tabuleiro, turno e resultado.
- [ ] `MOVE_RESULT(ACCEPTED/REJECTED)` segue o contrato; não há resposta duplicada contraditória com `ERROR`.
- [ ] Toda jogada inválida mantém estado e `revision` intactos.
- [ ] `BOARD` inicial e posterior chega a **ambos** os clientes; `GAME_OVER` chega aos dois quando possível.
- [ ] Fechamento de conexão, erro de rede e abandono têm transições previsíveis.
- [ ] Locks/filas evitam data races sem bloquear indefinidamente o servidor.
- [ ] Casos X vencedor, O vencedor, empate, células ocupadas, coordenadas inválidas e concorrência passam.
- [ ] `README.md`, `docs/*.md`, diagramas e planilha de etapas não contradizem o código.
- [ ] Testes foram executados; se algo não pôde ser testado, registrar a lacuna expressamente.
- [ ] Toda criação, alteração, remoção ou renomeação de arquivo está registrada em `docs/linha_do_tempo.md`.

## 12. Auditoria de ambiguidades identificadas na documentação de referência

As questões abaixo foram detectadas **nos documentos de planejamento**, não em código executável (nenhum repositório-fonte foi fornecido para auditoria). Este arquivo estabelece decisões claras para impedir implementações incompatíveis:

| Ambiguidade/falha potencial | Decisão padronizada em AGENTS.md | Correção documental recomendada |
|---|---|---|
| O PDF mostra `ERROR` para `OCCUPIED`, mas também define `MOVE_RESULT` como confirmação/rejeição de jogada. | Erro **semântico** de MOVE → `MOVE_RESULT(REJECTED)`; `ERROR` para protocolo/sessão. | Harmonizar exemplos do PDF e `docs/protocolo.md`. |
| O PDF usa `version` no exemplo de `MOVE`, mas não em todas as respostas. | Todas as mensagens usam `version: 1` e `type`. | Corrigir exemplos reduzidos nos documentos. |
| Definições de `connect/listen/accept` surgem tanto em Transporte quanto em Servidor. | Biblioteca fornece primitivas; **Servidor controla `listen/accept` e sessões**. | Explicitar fronteira nos diagramas e responsabilidades. |
| A documentação não fixa tamanho máximo nem critérios concretos de framing. | JSONL UTF-8, LF, **4096 bytes incluindo LF**, buffer persistente por conexão. | Registrar valor e testes em `docs/transporte.md`. |
| Um `BOARD` terminal não determina claramente o próximo turno. | `turn: null` quando houver WIN/DRAW/ABORTED; `revision` monotônica. | Atualizar esquema e exemplos. |
| O destino após desconexão ou abandono não está especificado em payload. | `GAME_OVER(result=ABORTED, winner=null, reason=OPPONENT_LEFT)`. | Atualizar catálogo de mensagens e diagrama de estados. |
| A planilha usa dependências preliminares que podem parecer circulares antes da aprovação do contrato. | Rascunho conjunto de T01–T03/C01/S01; **I01 aprova contrato** e libera implementação. | Ajustar explicação de pré-requisitos da etapa 0. |
| O nome expandido TTTP contém *Transport*, apesar de o protocolo ser de aplicação. | Conservar identificador **TTTP/1** do PDF, descrevendo corretamente sua camada. | Inserir esclarecimento na introdução do protocolo. |

## 13. Critério de conclusão do projeto

Uma entrega só estará **concluída** quando:

1. Três frentes estiverem integradas por um **contrato de aplicação único**.
2. O servidor aceitar pelo menos dois clientes e permitir uma partida inteira com turnos válidos.
3. Vitória X, vitória O, empate, erros de protocolo e desconexões forem demonstráveis.
4. Testes automatizados e testes de integração estiverem executados e registrados.
5. `README.md` permitir reproduzir a demonstração com comandos objetivos.
6. Diagramas, mensagens, estados e justificativa do TCP descreverem o comportamento **real** do código.

**Regra final para agentes:** priorize **correção e consistência verificável**, não recursos extras. Ao alterar o protocolo, atualize documentação, testes, cliente e servidor na mesma alteração coordenada. Nunca declare que uma funcionalidade foi implementada ou testada se ela ainda não existir ou não tiver sido efetivamente executada.

## 14. Registro obrigatório de modificações

`docs/linha_do_tempo.md` é o histórico cumulativo das modificações realizadas
no repositório por agentes de código.

### 14.1 Quando registrar

- Registrar toda operação que crie, altere, remova ou renomeie um arquivo.
- Fazer o registro na mesma mudança coordenada, antes de encerrar a tarefa.
- Uma única entrada pode agrupar vários arquivos quando todos pertencem ao
  mesmo objetivo ou tarefa.
- Inspeções somente de leitura, explicações em conversa e comandos que não
  alteram arquivos não exigem entrada.
- A edição da própria linha do tempo é parte da entrada da mudança que a
  motivou e não gera outra entrada separada.

### 14.2 Conteúdo mínimo da entrada

Cada entrada deve informar:

1. data e horário no fuso `America/Bahia`;
2. autor ou agente responsável;
3. tarefa, etapa ou objetivo;
4. arquivos criados, alterados, removidos ou renomeados;
5. descrição objetiva do estado anterior e do novo estado;
6. testes e verificações efetivamente executados, com o resultado;
7. pendências, lacunas de teste, aprovações ou validações ainda necessárias.

### 14.3 Integridade do histórico

- Manter as entradas em ordem cronológica.
- Não apagar ou reescrever uma entrada anterior para ocultar uma mudança.
- Corrigir um registro inexato por meio de uma nova entrada que identifique a
  correção e a entrada afetada.
- Não registrar como concluído ou testado aquilo que não foi executado.
- Não incluir segredos, credenciais, dados pessoais ou conteúdo sensível.
