# Interface gráfica e observabilidade das camadas

## Objetivo

Cliente e servidor possuem interfaces **PySide6 + Qt Quick/QML** separadas do
núcleo em `interface/`. Os controladores Python ficam em
`interface/client_window.py` e `interface/server_window.py`; a composição
visual fica em `interface/qml/`. As janelas demonstram o funcionamento real
das duas camadas do projeto:

```text
Cliente: Interface → aplicação cliente → shared.transport → TCP / servidor
Servidor: Clientes / TCP → shared.transport → aplicação servidor → Lobby + Game
```

`shared.transport` continua sendo uma biblioteca, não um terceiro processo. A
telemetria é somente local: ela não acrescenta campos às mensagens, não cria um
protocolo paralelo e não interfere quando nenhum observador está configurado.

## Execução e espelho PowerShell/CMD

Os pontos de entrada continuam sendo os mesmos:

```powershell
python -m server.server --host 127.0.0.1 --port 5000
python -m client.client --host 127.0.0.1 --port 5000
python -m client.client --host 127.0.0.1 --port 5000
```

Em um terminal interativo, a janela abre automaticamente e o terminal imprime
os mesmos eventos de aplicação e transporte. No cliente, os prompts textuais e
os controles gráficos chamam o mesmo controlador; uma jogada originada por
qualquer superfície produz o mesmo `MOVE` e só altera o tabuleiro após o
`BOARD` oficial.

A janela do cliente inicia automaticamente a conexão usando o `--host` e a
`--port` recebidos pelo mesmo comando. Se a tentativa falhar, a interface volta
ao estado desconectado e mantém os campos e o botão para uma nova tentativa.

- `--terminal-only`: executa somente a interface textual legada.
- `--gui`: força a GUI, inclusive com entrada/saída redirecionada.
- fechar/desconectar envia `QUIT` quando ainda for possível e encerra o canal.

## Composição aprovada das telas

### Cliente

- o tabuleiro 3×3 quadrado é o elemento principal da área de trabalho;
- conexão, marca, `game_id`, revisão e a explicação do estado autoritativo
  ficam em uma coluna secundária;
- o terminal TTTP/1 é uma gaveta inferior recolhida por padrão, aberta por
  clique ou arrasto vertical;
- a gaveta ocupa espaço real no layout: ao abrir, comprime suavemente a área
  principal em vez de ficar sobre ela;
- o tabuleiro reduz uniformemente e continua estritamente quadrado, assim
  como cada uma das nove células;
- a abertura usa 340 ms com desaceleração cúbica e o fechamento usa 250 ms,
  tornando a transição legível sem parecer travada;
- a barra mostra aplicação e transporte no mesmo registro que também é
  impresso no PowerShell/CMD.

### Servidor

- o topo mostra endereço do listener, total de sessões, lobby, partidas e o
  timeout de handshake;
- sessões e partida observada ocupam o painel esquerdo;
- a linha do tempo de aplicação/transporte ocupa o painel direito;
- iniciar e parar continuam controlando a mesma instância de `GameServer`;
- a fotografia de status inclui `game_id`, estado, turno e revisão somente para
  apresentação, sem criar mensagens de rede adicionais.

## O que cada camada demonstra

### Transporte

O observador opcional de `MessageChannel` apresenta:

- chamada de `socket.create_connection`, `sendall` e `recv`;
- serialização JSON, codificação UTF-8 e LF final;
- tamanho real do registro em bytes;
- reconstrução por buffer e quantidade residual depois do LF;
- objeto devolvido por `decode_message` à aplicação.

Uma exceção no observador é descartada e não quebra o canal. A telemetria não é
transmitida para a outra ponta.

### Aplicação do cliente

A janela mostra fase da sessão, `client_id`, `game_id`, marca, turno, revisão,
tabuleiro e resultado. O modelo de apresentação valida a sequência recebida,
mantém uma jogada pendente depois de `MOVE_RESULT(ACCEPTED)` e só atualiza a
célula quando chega o `BOARD` correspondente. `JOIN` após `GAME_OVER` reutiliza
a sessão TCP, mas exige outro `game_id`.

### Aplicação do servidor

O painel mostra listener, sessões, fila do lobby, partidas e a passagem por
handshake, pareamento, validação de jogada, atualização atômica, resultado e
aborto. Respostas aparecem primeiro como itens da fila da aplicação e depois
como registros efetivamente enviados pelo transporte.

## Sistema visual aplicado

A interface deriva de `design/DESIGN-coinbase.md`, usando substitutos locais
para as fontes licenciadas:

| Decisão do guia | Aplicação no projeto |
|---|---|
| Azul único `#0052ff` | Ações primárias, foco, badges ativos e marca X. |
| Canvas branco + cinza suave + hero `#0a0b0d` | Controles claros, faixa de trabalho suave e cabeçalho/painel de eventos escuros. |
| Display em peso 400 | Títulos editoriais em Segoe UI regular. |
| CoinbaseSans / CoinbaseMono | Segoe UI para texto; Consolas para revisões, bytes e JSONL. |
| Botões-pílula e badges | Conectar, iniciar, nova partida, estados e metadados. |
| Cartões com raio 24 px | Conexão, jogo, sessões e linha do tempo. |
| Campos com raio 12 px e foco azul | Host e porta. |
| Uma única sombra suave | Profundidade dos cartões claros, sem múltiplos níveis. |
| Cartões de produto sobrepostos em hero escuro | Motivo visual `APP`/`TCP` sobre a linha do tempo. |
| Verde/vermelho somente semântico | Reservados a sucesso/erro; nunca usados como CTA. |
| Ritmo baseado em 4 px | Espaçamentos de 8, 12, 16, 20, 24 e 32 px. |

## Critérios de IHC adotados

Os arquivos de `design/auditoria-ihc-nielsen-shneiderman/` foram usados como
critérios de projeto, não como certificação de acessibilidade:

| Critério | Implementação verificável |
|---|---|
| N1 / S3 — estado e feedback | Fase, turno, revisão, conexão e cada etapa da mensagem permanecem visíveis. |
| N4 / S1 — consistência | Mesmos nomes TTTP/1, cores, posição dos controles e fluxo nas duas janelas. |
| N5 / S5 — prevenção de erro | Células, conexão e nova partida ficam desabilitadas fora da fase válida. |
| N6 / S8 — reconhecimento | Pilha de camadas, limites e JSON atual permanecem visíveis; não é necessário memorizá-los. |
| N9 — recuperação | Falhas mostram camada, código/motivo e mantêm o tabuleiro oficial quando a jogada é rejeitada. |
| S2 — usabilidade universal | Botões e células aceitam mouse, `Tab`, `Enter` e `Espaço`; o terminal permanece disponível. |
| S4 — encerramento claro | `GAME_OVER`, nova partida e desconexão são estados e ações explícitos. |
| S7 — usuário no controle | É possível desconectar, fechar ou escolher entre GUI e modo textual. |

## Verificação

Os testes em `tests/test_interface.py` cobrem o modelo de apresentação, a
espera pelo `BOARD` oficial, rejeições sem mutação, revisões, novo `JOIN`,
eventos reais do transporte, isolamento de falhas do observador e telemetria do
servidor. `tests/test_qt_interface.py` carrega as duas telas QML com a
plataforma Qt fora de tela e verifica que a gaveta comprime a área principal,
que o tabuleiro permanece quadrado e que o painel inicia o `GameServer` real.
A renderização depende de `PySide6==6.12.0`, declarada em `requirements.txt`.
