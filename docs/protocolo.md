# TTTP/1 — Contrato de comunicação

## 1. Finalidade e escopo

Este documento registra a especificação-base da versão 1 do protocolo de
comunicação do Jogo da Velha Multiplayer. Ele corresponde à tarefa **T01 —
Definir o contrato de comunicação** da frente de Transporte e Protocolo.

**TTTP/1** é um protocolo próprio da camada de aplicação que opera sobre TCP.
Apesar da palavra *Transport* em seu nome de trabalho, o TTTP/1 não implementa
nem substitui o TCP.

A frente de Transporte fornece uma biblioteca compartilhada pelo cliente e pelo
servidor. Ela não constitui um terceiro processo, proxy ou servidor
intermediário.

Esta etapa fixa:

- o protocolo de transporte utilizado;
- a codificação dos dados;
- o formato e o enquadramento de cada registro;
- o tamanho máximo de uma mensagem;
- o identificador e a versão presentes no envelope;
- as regras gerais de envio e recepção;
- os limites de responsabilidade da camada compartilhada.

O catálogo completo de mensagens e seus payloads está na seção 7 e corresponde
a **T02**. A sequência nominal está na seção 8. O catálogo de erros e suas
reações está na seção 9 e corresponde a **T03**.

## 2. Requisitos normativos

Os termos **DEVE**, **NÃO DEVE** e **PODE** indicam, respectivamente, requisito
obrigatório, proibição e comportamento permitido pelo contrato.

### 2.1 Transporte

1. Cliente e servidor DEVEM trocar as mensagens do jogo por **sockets TCP**.
2. HTTP, REST, WebSocket e serviços externos NÃO DEVEM ser usados como
   mecanismo principal da comunicação do jogo.
3. Cada cliente DEVE manter sua própria conexão TCP com o servidor durante a
   sessão.
4. Uma conexão TCP PODE transportar várias mensagens de aplicação.
5. O TCP fornece um fluxo ordenado de bytes. Uma chamada a `recv()` NÃO DEVE
   ser interpretada como uma mensagem completa.

### 2.2 Codificação e representação

1. Cada mensagem DEVE ser representada por exatamente um **objeto JSON**.
2. O objeto JSON DEVE ser codificado em **UTF-8** antes do envio.
3. A raiz da mensagem NÃO DEVE ser uma lista, string, número, booleano ou
   `null`.
4. A ordem dos campos de um objeto JSON não possui significado semântico.
5. Espaços permitidos pela sintaxe JSON não alteram o significado da mensagem.
6. Caracteres Unicode PODEM ser enviados diretamente em UTF-8 ou escapados de
   modo válido pelo JSON. Após a decodificação, o valor textual resultante DEVE
   ser o mesmo.

### 2.3 Enquadramento JSONL

1. Cada objeto JSON codificado DEVE ser seguido por um único delimitador
   **LF (`\n`, byte `0x0A`)**.
2. O formato de transmissão é JSON por linha, também chamado JSONL.
3. O LF delimita registros e NÃO faz parte do conteúdo JSON entregue ao
   decodificador.
4. Nenhum outro delimitador de mensagem é definido pelo TTTP/1.
5. Uma quebra de linha dentro de uma string JSON DEVE aparecer escapada como
   `\n`. Um LF literal NÃO DEVE aparecer no meio de um registro.

Exemplo lógico:

```json
{"type":"HELLO","version":1}
```

Representação transmitida:

```python
b'{"type":"HELLO","version":1}\n'
```

### 2.4 Limite de tamanho

1. A constante normativa da versão 1 é `MAX_MESSAGE_BYTES = 4096`.
2. Cada mensagem DEVE ocupar no máximo **4096 bytes**, incluindo o LF final.
3. O limite DEVE ser calculado sobre os bytes codificados em UTF-8, e não sobre
   a quantidade de caracteres do texto.
4. O emissor NÃO DEVE enviar um registro acima do limite.
5. O receptor NÃO DEVE acumular dados sem limite enquanto procura o LF.
6. A reação formal a uma mensagem acima do limite será definida no catálogo de
   erros de T03.

Assim, uma mensagem é válida quanto ao tamanho somente quando:

```text
tamanho(JSON codificado em UTF-8) + 1 byte do LF <= 4096
```

### 2.5 Envelope comum

Todas as mensagens TTTP/1 DEVEM conter os campos abaixo:

| Campo | Tipo JSON | Regra |
|---|---|---|
| `type` | string | Identifica o tipo da mensagem. O valor usa grafia maiúscula e exata. |
| `version` | number inteiro | Deve possuir exatamente o valor `1`. Booleanos não são aceitos como inteiros. |

Envelope mínimo:

```json
{"type":"HELLO","version":1}
```

O campo `type` é o identificador de mensagem adotado pela versão 1. T01 não
introduz identificadores numéricos, `request_id`, `session_id` ou timestamps.
Os valores válidos de `type` e os demais campos permitidos para cada mensagem
serão definidos pelo catálogo de T02.

Os nomes dos campos, os valores de enumeração e os índices são sensíveis a
maiúsculas e minúsculas. Por exemplo, `type` e `Type` são nomes diferentes, e
`HELLO` e `hello` são valores diferentes.

### 2.6 Versionamento e compatibilidade

1. A constante normativa da versão inicial é `PROTOCOL_VERSION = 1`.
2. Todas as mensagens, em ambas as direções, DEVEM declarar `"version": 1`.
3. Não existe negociação automática de versão no TTTP/1.
4. Uma mensagem com outro valor de `version` é incompatível com a versão 1. A
   resposta e o fechamento controlado serão detalhados em T03.
5. Alterações incompatíveis no formato, nos campos ou na semântica exigem uma
   nova versão do protocolo e uma decisão explícita da equipe.
6. O contrato abaixo é a linha de base implementada no repositório. Qualquer
   mudança deliberada no TTTP/1 DEVE ser coordenada entre documentação,
   biblioteca compartilhada, testes, cliente e servidor.

## 3. Regras gerais de envio

Para enviar uma mensagem, a implementação DEVE executar, na ordem:

1. construir um objeto compatível com o esquema do tipo de mensagem;
2. validar o envelope e o payload;
3. serializar o objeto como JSON;
4. codificar o JSON em UTF-8;
5. verificar o limite após considerar o LF;
6. acrescentar o LF;
7. enviar o registro completo com `sendall()` ou mecanismo equivalente.

Todos os envios realizados sobre a mesma conexão DEVEM ser serializados por um
lock ou mecanismo equivalente. Duas threads NÃO DEVEM intercalar bytes de
registros diferentes.

## 4. Regras gerais de recepção

O receptor DEVE manter um buffer persistente separado para cada conexão.

O algoritmo de recepção DEVE:

1. preservar no buffer os bytes ainda não processados;
2. procurar o primeiro LF;
3. se não houver LF, receber mais bytes sem descartar o conteúdo existente;
4. controlar o tamanho do registro antes que o buffer cresça sem limite;
5. ao encontrar LF, retirar somente o registro terminado por esse delimitador;
6. manter no buffer todos os bytes posteriores ao LF;
7. decodificar o registro como UTF-8;
8. interpretar o conteúdo como um objeto JSON;
9. validar o envelope e, após T02, o payload do tipo correspondente.

Uma mensagem PODE chegar fragmentada entre várias leituras. Várias mensagens
PODEM chegar concatenadas em uma única leitura. Ambos os casos DEVEM produzir
os mesmos objetos que seriam recebidos em leituras separadas.

O retorno `b''` de `recv()` significa fim do fluxo TCP. Ele NÃO representa uma
mensagem de aplicação vazia.

## 5. Separação de responsabilidades

### 5.1 Transporte e protocolo compartilhado

A biblioteca compartilhada é responsável por:

- serialização e desserialização JSON;
- codificação e decodificação UTF-8;
- enquadramento JSONL;
- buffer persistente por conexão;
- limite de tamanho;
- validação estrutural do envelope e dos payloads;
- envio serializado;
- sinalização de EOF, timeout e falhas de socket.

Ela PODE disponibilizar primitivas de conexão, escuta e aceitação. A decisão de
quando conectar pertence ao cliente. A decisão de quando escutar, aceitar e
administrar sessões pertence ao servidor.

### 5.2 Regras que não pertencem ao transporte

A camada compartilhada NÃO DEVE:

- atribuir as marcas X ou O;
- escolher ou alterar o turno;
- validar se uma célula está ocupada;
- modificar o tabuleiro;
- determinar vitória ou empate;
- confiar em marca, turno ou vencedor informados pelo cliente.

Essas decisões pertencem ao servidor autoritativo e serão especificadas nas
frentes de Cliente e Servidor.

## 6. Critérios de verificação de T01

O contrato-base atende a T01 quando for possível responder de forma inequívoca:

- qual transporte é usado;
- como o JSON é codificado;
- como cada mensagem é delimitada;
- qual é o tamanho máximo e como ele é medido;
- como a mensagem é identificada;
- qual versão deve aparecer no envelope;
- como fragmentação e concatenação são tratadas;
- quais responsabilidades ficam fora da camada compartilhada.

Esta seção, a implementação compartilhada e os testes automatizados atendem
tecnicamente a T01. O marco I01 continua exigindo um registro de aprovação da
equipe para ser considerado formalmente concluído.

## 7. Catálogo de mensagens — T02

### 7.1 Regras comuns dos esquemas

1. Os esquemas desta seção são completos para a versão 1.
2. Todos os campos indicados em cada esquema são obrigatórios, salvo quando uma
   regra condicional declarar o contrário.
3. Campos não previstos pelo esquema do tipo não fazem parte do TTTP/1.
4. Campo ausente, campo inesperado ou valor com tipo JSON incorreto constitui
   `BAD_FORMAT`.
5. `version` diferente do inteiro `1` constitui `UNSUPPORTED_VERSION`.
6. `type` que seja uma string, mas não pertença ao catálogo, constitui
   `UNKNOWN_TYPE`.
7. Nos campos inteiros, valores booleanos não são aceitos como inteiros.
8. Os valores de enumeração usam a grafia exata apresentada nesta seção.
9. `client_id` e `game_id` são identificadores atribuídos pelo servidor. O
   cliente não os cria nem os substitui por valores próprios.

### 7.2 Visão geral

| Tipo | Origem | Destino | Finalidade |
|---|---|---|---|
| `HELLO` | Cliente | Servidor | Iniciar o handshake TTTP/1. |
| `WELCOME` | Servidor | Cliente | Confirmar o handshake e informar `client_id`. |
| `JOIN` | Cliente | Servidor | Solicitar entrada no lobby. |
| `WAITING` | Servidor | Cliente | Informar que o cliente aguarda adversário. |
| `START` | Servidor | Ambos os jogadores | Informar `game_id`, marca e primeiro turno. |
| `MOVE` | Cliente | Servidor | Solicitar uma jogada na partida indicada. |
| `MOVE_RESULT` | Servidor | Solicitante da jogada | Confirmar ou rejeitar um `MOVE`. |
| `BOARD` | Servidor | Ambos os jogadores | Publicar o snapshot oficial do tabuleiro. |
| `GAME_OVER` | Servidor | Ambos os jogadores | Informar vitória, empate ou aborto. |
| `ERROR` | Servidor | Cliente relacionado ao erro | Informar erro de formato, protocolo ou estado da sessão. |
| `PING` | Ambos | Outra ponta | Sondagem opcional de atividade. |
| `PONG` | Ambos | Outra ponta | Resposta opcional a `PING`. |
| `QUIT` | Cliente | Servidor | Solicitar encerramento da sessão. |

`PING` e `PONG` pertencem ao catálogo, mas são opcionais na primeira entrega.
Nenhuma ponta pode depender deles até a extensão ser implementada e testada.

### 7.3 `HELLO`

Inicia a sessão lógica depois da abertura do socket TCP.

```json
{"type":"HELLO","version":1}
```

Campos: somente o envelope comum.

### 7.4 `WELCOME`

Confirma que o servidor aceitou o handshake da versão 1.

```json
{"type":"WELCOME","version":1,"client_id":"c42"}
```

| Campo | Tipo | Regra |
|---|---|---|
| `client_id` | string | Identificador da sessão lógica atribuído pelo servidor. |

### 7.5 `JOIN`

Solicita a entrada do cliente identificado no lobby. O servidor aceita
`JOIN` após o handshake inicial e também depois de `GAME_OVER`, enquanto a
conexão permanecer aberta. No segundo caso, a sessão volta ao lobby para uma
nova partida.

```json
{"type":"JOIN","version":1}
```

Campos: somente o envelope comum. Um `JOIN` posterior a `GAME_OVER` não
recupera o `game_id` encerrado: o próximo `START` usa outro identificador,
`BOARD` começa em `revision: 0` e o pareamento não garante o mesmo
adversário.

### 7.6 `WAITING`

Informa que o cliente entrou no lobby e aguarda adversário.

```json
{"type":"WAITING","version":1}
```

Campos: somente o envelope comum.

### 7.7 `START`

Informa a formação da partida. O servidor envia um `START` para cada
participante, usando o mesmo `game_id`, marcas distintas e `first_turn` igual a
`X`.

```json
{"type":"START","version":1,"game_id":"g17","mark":"X","first_turn":"X"}
```

| Campo | Tipo | Regra |
|---|---|---|
| `game_id` | string | Identificador da partida atribuído pelo servidor. |
| `mark` | string | Exatamente `"X"` ou `"O"`. |
| `first_turn` | string | Exatamente `"X"` na versão 1. |

### 7.8 `MOVE`

Solicita uma jogada. O cliente envia a intenção, mas não informa marca, turno,
revisão, vencedor ou novo tabuleiro.

```json
{"type":"MOVE","version":1,"game_id":"g17","row":1,"col":2}
```

| Campo | Tipo | Regra |
|---|---|---|
| `game_id` | string | Partida na qual o cliente pretende jogar. |
| `row` | number inteiro | Índice de linha. Booleanos e números fracionários são inválidos. |
| `col` | number inteiro | Índice de coluna. Booleanos e números fracionários são inválidos. |

Os valores válidos de `row` e `col` são de 0 a 2. Um inteiro fora dessa faixa é
uma mensagem estruturalmente legível, mas a jogada é rejeitada semanticamente
com `INVALID_POSITION`.

### 7.9 `MOVE_RESULT`

Informa ao solicitante o resultado de um `MOVE`. Existem duas variantes
exclusivas.

#### 7.9.1 Jogada aceita

```json
{"type":"MOVE_RESULT","version":1,"game_id":"g17","status":"ACCEPTED","row":1,"col":2,"revision":1}
```

| Campo | Tipo | Regra |
|---|---|---|
| `game_id` | string | Partida afetada. |
| `status` | string | Exatamente `"ACCEPTED"`. |
| `row` | number inteiro | Linha efetivamente alterada, entre 0 e 2. |
| `col` | number inteiro | Coluna efetivamente alterada, entre 0 e 2. |
| `revision` | number inteiro | Nova revisão da partida, maior ou igual a 1. |

#### 7.9.2 Jogada rejeitada

```json
{"type":"MOVE_RESULT","version":1,"game_id":"g17","status":"REJECTED","code":"OCCUPIED","message":"Posição já ocupada"}
```

| Campo | Tipo | Regra |
|---|---|---|
| `game_id` | string | Partida indicada na solicitação. |
| `status` | string | Exatamente `"REJECTED"`. |
| `code` | string | Código semântico de `MOVE` definido na seção 9. |
| `message` | string | Texto de apresentação ou log. A lógica não depende desta frase. |

As variantes são mutuamente exclusivas. A variante aceita usa `row`, `col` e
`revision`. A variante rejeitada usa `code` e `message`.

### 7.10 `BOARD`

Publica o snapshot oficial da partida.

```json
{"type":"BOARD","version":1,"game_id":"g17","board":[["","",""],["","",""],["","",""]],"turn":"X","revision":0}
```

| Campo | Tipo | Regra |
|---|---|---|
| `game_id` | string | Partida do snapshot. |
| `board` | array | Matriz com exatamente três linhas e três células por linha. |
| `turn` | string ou `null` | `"X"` ou `"O"` durante a partida; `null` em snapshot terminal. |
| `revision` | number inteiro | Começa em 0 e nunca diminui. Booleanos não são aceitos. |

Cada célula de `board` contém exatamente `"X"`, `"O"` ou `""`. A posição
`board[0][0]` representa o canto superior esquerdo.

O `BOARD` inicial tem tabuleiro vazio, `turn: "X"` e `revision: 0`. Cada jogada
aceita incrementa `revision` exatamente uma vez. Jogada rejeitada não modifica
tabuleiro, turno nem revisão. Todo `BOARD` que represente estado finalizado usa
`turn: null`, seja o término por vitória, empate ou aborto.

### 7.11 `GAME_OVER`

Finaliza a partida para ambos os participantes. Existem três variantes.

Vitória:

```json
{"type":"GAME_OVER","version":1,"game_id":"g17","result":"WIN","winner":"X"}
```

Empate:

```json
{"type":"GAME_OVER","version":1,"game_id":"g17","result":"DRAW","winner":null}
```

Aborto por saída do adversário:

```json
{"type":"GAME_OVER","version":1,"game_id":"g17","result":"ABORTED","winner":null,"reason":"OPPONENT_LEFT"}
```

| Campo | Tipo | Regra |
|---|---|---|
| `game_id` | string | Partida encerrada. |
| `result` | string | Exatamente `"WIN"`, `"DRAW"` ou `"ABORTED"`. |
| `winner` | string ou `null` | `"X"` ou `"O"` em vitória; `null` em empate ou aborto. |
| `reason` | string | Obrigatório e igual a `"OPPONENT_LEFT"` somente em aborto. |

`reason` não pertence às variantes `WIN` e `DRAW`. Abandono não é convertido
automaticamente em vitória na versão 1.

### 7.12 `ERROR`

Informa problema de formato, protocolo ou estado da sessão. Rejeições
semânticas de uma jogada bem formada não usam `ERROR`.

```json
{"type":"ERROR","version":1,"code":"BAD_FORMAT","message":"Mensagem inválida"}
```

| Campo | Tipo | Regra |
|---|---|---|
| `code` | string | Código de erro definido na seção 9. |
| `message` | string | Texto de apresentação ou log, sem detalhes internos do servidor. |

### 7.13 `PING` e `PONG`

Mensagens opcionais para sondagem de atividade.

```json
{"type":"PING","version":1}
```

```json
{"type":"PONG","version":1}
```

Campos: somente o envelope comum. Se essa extensão for implementada, o receptor
de `PING` responde com `PONG`. Ela não deve interferir no turno ou no estado do
jogo.

### 7.14 `QUIT`

Solicita o encerramento da sessão. O catálogo não define uma mensagem `BYE`.

```json
{"type":"QUIT","version":1}
```

Campos: somente o envelope comum. Após processar `QUIT`, o servidor encerra a
sessão e aplica a política de saída do lobby ou de aborto da partida.

## 8. Sequência nominal de eventos

1. O cliente abre o socket TCP e envia `HELLO`.
2. O servidor valida a versão e responde `WELCOME` com `client_id`.
3. O cliente envia `JOIN`.
4. Sem adversário disponível, o servidor envia `WAITING`.
5. Com dois participantes válidos, o servidor envia `START` aos dois, com o
   mesmo `game_id`, marcas diferentes e `first_turn: "X"`.
6. O servidor envia o `BOARD` inicial aos dois, com `revision: 0`.
7. Somente o jogador do turno envia `MOVE`.
8. Em jogada aceita, o servidor envia `MOVE_RESULT` com `ACCEPTED` ao
   solicitante e depois envia o novo `BOARD` aos dois.
9. Se a jogada encerrou a partida, depois do `BOARD` o servidor envia
   `GAME_OVER` aos dois.
10. Em jogada inválida, o servidor envia somente `MOVE_RESULT` com `REJECTED`
    ao solicitante. Não envia `BOARD` e não altera a revisão.
11. `QUIT`, EOF ou falha de conexão encerram a sessão. Se o cliente estava em
    partida ativa, o servidor tenta notificar o adversário com
    `GAME_OVER(result="ABORTED", reason="OPPONENT_LEFT")`.
12. Depois de `GAME_OVER`, uma sessão ainda conectada pode enviar novo
    `JOIN` para voltar ao lobby ou `QUIT` para encerrar. Um novo pareamento
    envia outro `START` e outro `BOARD(revision=0)`; não reabre a partida
    anterior.

A ordem lógica por conexão deve ser preservada. Para o solicitante de uma
jogada terminal aceita, a ordem é `MOVE_RESULT`, `BOARD`, `GAME_OVER`.

## 9. Catálogo de erros e respostas — T03

### 9.1 Classes de erro

O TTTP/1 separa os erros em três grupos:

- erro de formato, protocolo ou estado de sessão: resposta `ERROR`;
- rejeição semântica de `MOVE` bem formado: resposta
  `MOVE_RESULT(status="REJECTED")`;
- falha local de transporte, como timeout sem conexão utilizável: tratamento
  local, sem presumir que uma resposta de rede é possível.

O servidor NÃO DEVE enviar `ERROR` e `MOVE_RESULT` para a mesma rejeição. Uma
jogada rejeitada NÃO DEVE alterar tabuleiro, turno, revisão, vencedor ou estado
da partida.

### 9.2 Códigos

| Código | Condição | Resposta e efeito |
|---|---|---|
| `BAD_FORMAT` | UTF-8 ou JSON inválido; raiz diferente de objeto; campo obrigatório ausente; campo inesperado; campo com tipo incorreto. | Enviar `ERROR` quando possível. Não modificar a partida. |
| `UNKNOWN_TYPE` | `type` é uma string, mas não pertence ao catálogo TTTP/1. | Enviar `ERROR`. Não modificar a partida e manter a sessão quando possível. |
| `UNSUPPORTED_VERSION` | `version` é inteiro, mas diferente de 1. | Enviar `ERROR` na versão 1 e fechar a conexão de forma controlada. |
| `MESSAGE_TOO_LARGE` | O registro excede 4096 bytes, incluindo LF, ou o buffer atinge o limite sem encontrar LF. | Enviar `ERROR` se ainda for possível e fechar a conexão. |
| `INVALID_STATE` | `HELLO` ou `JOIN` recebido fora da fase permitida, ou outro comando incompatível com o estado da sessão. | Enviar `ERROR`; manter ou encerrar a sessão conforme a gravidade, sem modificar a partida indevidamente. |
| `NOT_IN_GAME` | `MOVE` sem participação em partida ativa ou com `game_id` alheio. | Enviar somente `MOVE_RESULT(REJECTED)`. Não modificar a partida. |
| `NOT_YOUR_TURN` | `MOVE` recebido de participante que não possui o turno atual. | Enviar somente `MOVE_RESULT(REJECTED)`. Não modificar a partida. |
| `INVALID_POSITION` | `row` ou `col` é inteiro fora da faixa de 0 a 2. | Enviar somente `MOVE_RESULT(REJECTED)`. Não modificar a partida. |
| `OCCUPIED` | A célula indicada já contém `"X"` ou `"O"`. | Enviar somente `MOVE_RESULT(REJECTED)`. Não modificar a partida. |
| `GAME_FINISHED` | `MOVE` recebido depois do encerramento da partida. | Enviar somente `MOVE_RESULT(REJECTED)`. Não modificar a partida. |
| `TIMEOUT` | Uma operação de conexão ou espera ultrapassa a política local configurada. | Tratar como evento local de transporte ou sessão. Responder somente se a conexão ainda permitir. |

### 9.3 Regras do campo `message`

1. A aplicação decide o comportamento pelo campo `code`, nunca comparando a
   frase de `message`.
2. `message` serve somente para apresentação ao usuário ou registro em log.
3. `message` NÃO DEVE expor traceback, caminho de arquivo, pilha de execução,
   conteúdo sensível ou detalhes de exceções internas.
4. A tradução ou alteração do texto não muda a semântica do código.

### 9.4 Formas canônicas de resposta

Erro de protocolo ou sessão:

```json
{"type":"ERROR","version":1,"code":"BAD_FORMAT","message":"Mensagem inválida"}
```

Rejeição de jogada:

```json
{"type":"MOVE_RESULT","version":1,"game_id":"g17","status":"REJECTED","code":"NOT_YOUR_TURN","message":"Não é o seu turno"}
```

## 10. Critérios de verificação de T02 e T03

T02 está especificado quando cada tipo exigido possui direção, finalidade,
campos, tipos, enumerações e exemplo JSON completo. O catálogo inclui `HELLO`,
`WELCOME`, `JOIN`, `WAITING`, `START`, `MOVE`, `MOVE_RESULT`, `BOARD`,
`GAME_OVER`, `ERROR`, `PING`, `PONG` e `QUIT`.

T03 está especificado quando cada código possui condição, forma de resposta e
efeito sobre sessão ou partida. O catálogo inclui `BAD_FORMAT`, `UNKNOWN_TYPE`,
`UNSUPPORTED_VERSION`, `MESSAGE_TOO_LARGE`, `INVALID_STATE`, `NOT_IN_GAME`,
`NOT_YOUR_TURN`, `INVALID_POSITION`, `OCCUPIED`, `GAME_FINISHED` e `TIMEOUT`.

T01, T02 e T03 estão implementados e cobertos pelos testes do contrato. O marco
I01 permanece em andamento até existir um registro explícito de aprovação
conjunta do contrato, do fluxo do cliente em C01 e dos estados do servidor em
S01.

## 11. Correspondência com a implementação — T13

O contrato deste documento é materializado pela API pública de `shared`:

| Regra do contrato | Implementação |
|---|---|
| versão 1 e limite de 4096 bytes | `PROTOCOL_VERSION` e `MAX_MESSAGE_BYTES` |
| envelope comum | `validate_envelope()` |
| campos, tipos, enumerações e variantes | `validate_payload()` |
| direção cliente → servidor | `validate_client_message()` |
| direção servidor → cliente | `validate_server_message()` |
| criação com envelope canônico | `make_message()` |
| JSON UTF-8 com LF e limite | `encode_message()` |
| decodificação de um registro delimitado | `decode_message()` |
| buffer, envio e recepção TCP | `MessageChannel` em `shared/transport.py` |

As validações acima são sintáticas e estruturais. Turno, participação,
ocupação, vencedor, empate e mutação do tabuleiro continuam sob autoridade do
servidor; não pertencem a `shared/protocol.py`.

Os testes canônicos estão em `tests/test_protocol.py`, e os testes de
enquadramento estão em `tests/test_transport.py`. O comportamento de TCP,
timeouts, EOF, locks, PING/PONG e o procedimento de captura estão detalhados em
[`transporte.md`](transporte.md).

Para verificar o contrato e o transporte:

```powershell
python -m unittest tests.test_protocol tests.test_transport tests.test_integration -v
```
