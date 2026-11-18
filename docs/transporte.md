# Transporte TCP e enquadramento TTTP/1

Este documento descreve o comportamento implementado em `shared/transport.py`
e sua relação com o protocolo de aplicação TTTP/1. O módulo é uma biblioteca
compartilhada por cliente e servidor. Ele não é um terceiro processo e não
contém regras do jogo.

O contrato normativo dos tipos de mensagem, campos e códigos está em
[`protocolo.md`](protocolo.md).

## 1. Por que TCP

O projeto precisa entregar mensagens entre dois clientes e um servidor com
ordem e confiabilidade. TCP fornece um fluxo de bytes ordenado, detecção de fim
de fluxo e retransmissão pelo sistema operacional. Isso permite concentrar o
trabalho do protocolo próprio em serialização, enquadramento e validação.

TCP não preserva fronteiras de mensagens. Um `sendall()` pode chegar em vários
`recv()`, e um único `recv()` pode conter vários envios. Por isso, o TTTP/1
define seu próprio enquadramento JSONL e mantém um buffer por conexão.

HTTP, WebSocket e REST não participam do transporte principal deste projeto.

## 2. Fronteiras de responsabilidade

| Componente | Responsabilidade |
|---|---|
| `shared/protocol.py` | Define versão, limite, catálogo, esquemas, validação e codificação JSONL. Não abre sockets. |
| `shared/transport.py` | Abre, aceita, envia, recebe e fecha conexões TCP; mantém buffer e locks. Não decide turno, tabuleiro ou vencedor. |
| `client/client.py` | Decide quando conectar e quais comandos válidos enviar. |
| `server/server.py` | Decide quando escutar, aceitar e administrar as sessões. |

As primitivas de escuta e aceitação pertencem à biblioteca, mas o laço de
`accept()` e o ciclo de vida dos clientes pertencem ao servidor.

## 3. Formato no fio

Cada mensagem TTTP/1 é:

1. um objeto JSON;
2. codificado em UTF-8;
3. terminado por um byte LF (`0A` hexadecimal, `\n` em Python);
4. limitado a 4096 bytes, incluindo o LF.

Exemplo de registro completo:

```text
{"type":"HELLO","version":1}\n
```

Toda mensagem contém `type` e `version`. A serialização usa JSON compacto e
preserva texto Unicode. Uma quebra de linha dentro de uma string JSON é
escapada como os dois caracteres `\` e `n`; ela não cria um segundo registro.

## 4. Enquadramento e buffer de recepção

Cada `MessageChannel` possui um buffer persistente, exclusivo da conexão. O
algoritmo de `receive_message()` executa as etapas abaixo:

1. procura LF no buffer existente;
2. se encontrou, retira somente o primeiro registro e mantém os bytes
   posteriores para a próxima chamada;
3. rejeita o registro se seu tamanho, incluindo LF, exceder 4096 bytes;
4. se ainda não encontrou LF, limita a próxima leitura à capacidade restante;
5. acumula o bloco recebido e repete a procura;
6. interpreta `recv() == b""` como EOF, fecha o canal e gera
   `ConnectionClosedError`;
7. entrega somente um registro completo a `decode_message()`.

Esse procedimento trata as duas situações que TCP pode produzir:

- **fragmentação:** uma mensagem distribuída por várias leituras;
- **concatenação:** duas ou mais mensagens presentes na mesma leitura.

O lock de recepção impede duas threads de consumirem simultaneamente o mesmo
buffer. Os wrappers que recebem um socket bruto registram e reutilizam o mesmo
`MessageChannel`, preservando os bytes residuais entre chamadas.

## 5. Envio robusto

`send_message()` valida e codifica todo o objeto antes de acessar o socket. O
registro completo é enviado com `sendall()` sob um lock exclusivo por conexão.
Assim, duas threads não intercalam bytes de mensagens distintas.

Uma falha ou timeout durante `sendall()` fecha o canal. Depois de um envio
parcial não há como saber com segurança qual prefixo chegou ao outro lado, logo
a conexão não é reutilizada.

## 6. API pública

| API | Comportamento |
|---|---|
| `MessageChannel(socket)` | Cria um canal com buffer e locks próprios. |
| `connect_to_server(host, port, timeout=...)` | Abre a conexão do cliente. O timeout limita apenas a tentativa de conexão; depois o socket volta ao modo bloqueante. |
| `create_listening_socket(host, port, ...)` | Cria, associa e coloca um socket TCP em escuta. |
| `accept_connection(listener)` | Aceita uma conexão e retorna um `MessageChannel` e o endereço remoto. |
| `send_message(connection, payload)` | Envia um registro JSONL completo. |
| `receive_message(connection)` | Retorna exatamente uma mensagem, sem perder registros posteriores. |
| `close_connection(connection)` | Fecha o canal de modo idempotente. |
| `set_timeout()` / `get_timeout()` | Configura ou consulta a política local de um canal. |
| `send_ping(connection)` | Envia o heartbeat opcional `PING`. |
| `handle_heartbeat_message(connection, message)` | Responde `PONG` a `PING`, consome `PONG` e não altera o estado do jogo. |

Cliente e servidor devem importar essa API comum por `shared`. Não devem criar
outro algoritmo de serialização ou enquadramento.

`MessageChannel` aceita opcionalmente um observador de `shared.telemetry`. Ele
recebe eventos locais após o envio completo e após a reconstrução/decodificação
de um registro, incluindo bytes e buffer residual. O observador não modifica o
payload, não envia telemetria pela rede e suas exceções são isoladas do canal.
Essa API alimenta as janelas didáticas descritas em
[`interface_grafica.md`](interface_grafica.md).

## 7. Falhas, EOF e timeout

| Condição | Exceção local | Estado do canal |
|---|---|---|
| EOF em `recv()` | `ConnectionClosedError` | fechado |
| socket falha ao receber | `SocketOperationError` | fechado |
| socket falha ou expira ao enviar | `SocketOperationError` ou `TransportTimeoutError` | fechado |
| recepção expira | `TransportTimeoutError` | aberto; buffer parcial preservado |
| registro excede 4096 bytes | `MessageTooLargeError` | ainda aberto para a camada de sessão tentar `ERROR`; deve ser fechado em seguida |
| UTF-8 ou JSON inválido | `MessageDecodingError` | aberto; camada de sessão decide a resposta |
| versão não suportada | `UnsupportedVersionError` | aberto; camada de sessão envia `ERROR` se possível e fecha |

O timeout de conexão ou handshake pode ser curto e configurável. O tempo de
reflexão de uma jogada não deve herdar automaticamente esse timeout. Um timeout
de recepção não descarta bytes já recebidos, permitindo continuar a montagem do
mesmo registro se a política da sessão mantiver a conexão.

Não se presume que seja possível enviar uma resposta depois de EOF ou falha do
socket. A camada de sessão trata a saída do lobby ou o aborto da partida e tenta
avisar o adversário, nunca o socket que já foi perdido.

## 8. PING/PONG opcional

O transporte oferece as primitivas de PING/PONG, mas não ativa um heartbeat
periódico. A política de periodicidade, tolerância e encerramento pertence aos
loops de cliente e servidor e precisa ser aprovada e testada antes de ser usada.
O jogo funciona sem PING/PONG na primeira entrega.

## 9. Testes de enquadramento — T11

Execute toda a suíte a partir da raiz:

```powershell
python -m unittest discover -s tests -v
```

Para executar apenas protocolo, transporte e demonstração TCP:

```powershell
python -m unittest tests.test_protocol tests.test_transport tests.test_integration -v
```

Os testes automatizados cobrem:

- mensagens fragmentadas em leituras pequenas;
- várias mensagens concatenadas em uma leitura;
- preservação de Unicode em UTF-8;
- UTF-8 e JSON inválidos;
- registro exatamente no limite e acima de 4096 bytes;
- EOF, timeout parcial e falhas de socket;
- múltiplos envios concorrentes sem intercalação;
- conexão real de loopback e sockets reais conectados;
- troca `HELLO/WELCOME`, `PING/PONG` e `QUIT` pelo TCP.

## 10. Inspeção no Wireshark — T12

O utilitário `tools/traffic_demo.py` produz uma sequência curta e previsível em
TCP real. Ele existe para captura técnica; não substitui cliente e servidor do
jogo.

### 10.1 Procedimento recomendado

1. Inicie o Wireshark e selecione a interface de loopback do Npcap.
2. Inicie a captura.
3. Use o filtro de exibição `tcp.port == 5000`.
4. Na raiz do projeto, execute:

   ```powershell
   python -m tools.traffic_demo --host 127.0.0.1 --port 5000 --delay 0.5
   ```

5. Aguarde o utilitário mostrar `HELLO`, `WELCOME`, `PING`, `PONG` e `QUIT`.
6. Pare a captura e use **Follow > TCP Stream** para observar o fluxo JSONL.
7. Salve a evidência, se solicitada, como `evidencias/tttp_demo.pcapng`.

Na captura, confirme:

- estabelecimento TCP (`SYN`, `SYN/ACK`, `ACK`);
- payload JSON em UTF-8 terminado por LF;
- a mesma conexão transportando várias mensagens TTTP/1;
- encerramento TCP por `FIN/ACK` ou, em falha, `RST`;
- ausência de HTTP ou WebSocket no fluxo principal.

### 10.2 Limites de visibilidade

Wireshark observa segmentos TCP, não as chamadas `sendall()` e `recv()` da
aplicação. Uma mensagem pode aparecer dividida em segmentos, e várias mensagens
podem compartilhar um segmento. Offloading da placa e captura em loopback podem
alterar a segmentação exibida. A opção **Follow TCP Stream** reconstrói o fluxo,
mas não valida regras como turno, ocupação de célula ou vencedor.

O JSON não é criptografado; a captura local consegue ler o conteúdo. Mesmo
assim, o Wireshark não conhece automaticamente o esquema TTTP/1 e não prova,
sozinho, que a aplicação rejeitou todos os payloads inválidos.

### 10.3 Estado da evidência neste ambiente

Na última verificação documental, em 2026-11-18, nenhum arquivo `.pcapng`
existia no repositório. Na tentativa de captura registrada anteriormente,
`Wireshark`, `TShark` e `dumpcap` não estavam instalados. O
`PktMon` estava disponível, mas o driver recusou a captura por falta de
privilégio. Portanto, nenhum arquivo `.pcapng` foi produzido ou validado aqui.
O gerador de tráfego e o procedimento acima são reproduzíveis, mas a evidência
visual de T12 ainda precisa ser coletada em uma sessão com capturador disponível.

Como alternativa em um PowerShell elevado, o Windows pode gerar um arquivo
convertível para Wireshark:

```powershell
New-Item -ItemType Directory -Force evidencias
pktmon filter remove
pktmon filter add TTTP -t TCP -p 5000
pktmon start --capture --pkt-size 0 --file-name evidencias\tttp_demo.etl
# Em outro terminal: python -m tools.traffic_demo --port 5000 --delay 0.5
pktmon stop
pktmon etl2pcap evidencias\tttp_demo.etl --out evidencias\tttp_demo.pcapng
pktmon filter remove
```

Esses comandos são instruções de reprodução. A captura alternativa não foi
executada com sucesso no ambiente atual.
