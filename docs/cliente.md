# C01 — Especificação do fluxo do cliente

## 1. Objetivo

Definir a jornada de utilização do cliente do Jogo da Velha, desde a conexão com o servidor até o encerramento da partida.

O cliente será responsável pela interação com o jogador, pela comunicação com o servidor e pela apresentação das informações recebidas.

O servidor permanece como autoridade sobre o estado da partida, as jogadas, os turnos e os resultados.

## 2. Interface inicial

A aplicação utilizará inicialmente uma interface de terminal, com o seguinte menu:

```text
================================
          JOGO DA VELHA
================================

1 - Conectar e jogar
2 - Sair

Escolha uma opção:
```

Ao selecionar a opção 1, o jogador iniciará o processo de conexão com o servidor.

Ao selecionar a opção 2, a aplicação será encerrada.

## 3. Fluxo principal do jogador

### 3.1 Conexão

O jogador escolhe iniciar uma partida. O cliente solicita ou utiliza o endereço IP e a porta do servidor e tenta estabelecer uma conexão TCP utilizando `shared.transport`.

### 3.2 Identificação

Após estabelecer a conexão, o cliente envia a mensagem `HELLO` e aguarda a resposta `WELCOME`.

### 3.3 Espera

Após a identificação, o cliente envia `JOIN` para entrar na fila de partidas.

Se não houver outro jogador disponível, recebe `WAITING` e apresenta uma mensagem informando que está aguardando um adversário.

### 3.4 Início da partida

Quando dois jogadores estiverem disponíveis, o cliente recebe `START`, contendo o identificador da partida (`game_id`), seu símbolo (`X` ou `O`) e as informações do primeiro turno.

O cliente apresenta o tabuleiro inicial recebido por meio de `BOARD`.

### 3.5 Jogadas

Quando for a vez do jogador, o cliente permite selecionar uma linha e uma coluna, ambas entre 0 e 2.

A jogada é enviada ao servidor por meio da mensagem `MOVE`.

O cliente não altera o tabuleiro por conta própria. Aguarda a confirmação e a atualização oficial recebida do servidor.

### 3.6 Resultado e atualização

O cliente confere se `MOVE_RESULT` pertence ao jogo atual e corresponde à linha e coluna enviadas. Em respostas aceitas, a revisão deve avançar em um e coincidir com a revisão do `BOARD` seguinte. Cada snapshot deve pertencer ao mesmo `game_id`, avançar exatamente uma revisão e representar uma única jogada válida. O cliente também confere que `GAME_OVER` corresponde ao estado final do tabuleiro.

Também permanece preparado para receber atualizações decorrentes das jogadas do adversário.

As informações apresentadas na interface devem corresponder ao estado confirmado pelo servidor.

### 3.7 Término

Quando a partida terminar, o cliente confere se `GAME_OVER` pertence ao `game_id` atual e se o resultado corresponde ao tabuleiro final. Depois apresenta o resultado e atualiza o placar da sessão: vitórias do jogador local, vitórias do adversário e empates. Como as marcas podem alternar entre revanches, o placar acompanha os jogadores, não as marcas. O placar usa o resultado oficial do servidor e não é salvo após fechar a conexão.

O cliente pode pedir revanche sem fechar a conexão. Envia `JOIN` após `GAME_OVER(WIN|DRAW)`; ambos precisam solicitar a revanche. O servidor inicia uma nova partida com outro `game_id`, e o cliente reinicia a revisão esperada em zero. Enviar `QUIT` encerra a sessão. Se a conexão fechar porque o outro jogador recusou, o cliente encerra a sequência e apresenta o placar final.

- Vitória;
- Derrota;
- Empate;
- Partida interrompida.

### 3.8 Saída

Ao encerrar a sessão, o cliente envia `QUIT`, quando possível, fecha a conexão e retorna ao menu ou encerra a aplicação.

## 4. Casos de uso

| Situação | Comportamento esperado |
|---|---|
| Servidor indisponível | Informar que não foi possível conectar. |
| Identificação aceita | Prosseguir para o lobby. |
| Jogador aguardando | Exibir mensagem de espera. |
| Partida iniciada | Exibir símbolo e tabuleiro inicial. |
| Coordenada inválida | Solicitar uma nova entrada. |
| Jogador sem turno | Informar que deve aguardar. |
| Célula ocupada | Apresentar a rejeição sem alterar o tabuleiro. |
| Jogada aceita | Atualizar após receber o estado oficial. |
| Adversário realiza jogada | Receber e apresentar a atualização. |
| Vitória, derrota ou empate | Exibir o resultado informado pelo servidor. |
| Adversário desconectado | Informar o encerramento ou abandono da partida. |
| Revanche | Atualizar e mostrar o placar; iniciar outra partida somente se ambos aceitarem. |
| Jogador decide sair | Encerrar a sessão adequadamente. |

## 5. Regras de responsabilidade

1. O cliente não determina quem venceu.
2. O cliente não decide de quem é a vez.
3. O cliente não considera uma jogada aceita antes da confirmação do servidor.
4. O cliente não modifica o tabuleiro oficial por conta própria.
5. As mensagens devem respeitar o protocolo TTTP/1 definido em `docs/protocolo.md`.
6. A comunicação TCP deve utilizar as funções compartilhadas de `shared/transport.py`.
7. A interface deve continuar permitindo o recebimento de mensagens da rede durante a partida.

## 6. Sequência resumida

```text
MENU
  |
  v
CONEXÃO TCP
  |
  v
HELLO -> WELCOME
  |
  v
JOIN
  |
  v
WAITING (se necessário)
  |
  v
START -> BOARD
  |
  v
JOGADAS (MOVE)
  |
  v
MOVE_RESULT -> BOARD
  |
  v
GAME_OVER
  |
  +---- placar atualizado
  |
  +---- JOIN (ambos aceitam) -> START -> BOARD -> nova partida
  |
  +---- QUIT / recusa -> ENCERRAMENTO
```

## 7. Dependências e situação

- Dependência indicada na planilha: T02.
- O catálogo de mensagens está documentado em `docs/protocolo.md`.
- A implementação do transporte está em `shared/transport.py`.
- A aprovação conjunta do marco I01 ainda precisa ser confirmada pela equipe.

**Situação:** especificação C01 elaborada.


---

# C02 a C13 — Implementação do cliente

## 8. Interface do tabuleiro

Foi implementada uma interface de terminal para representar o tabuleiro 3×3.

O tabuleiro começa vazio e apresenta as marcas X e O conforme as atualizações recebidas do servidor.

Também foi implementada a solicitação de linha e coluna ao jogador, com validação das coordenadas entre 1 e 3 na interface e conversão para o intervalo de 0 a 2 utilizado pelo protocolo.

## 9. Comunicação com o servidor

O cliente utiliza TCP por meio de `shared.transport`.

A conexão é estabelecida com o endereço e a porta informados na execução.

Após conectar, o cliente envia HELLO, aguarda WELCOME e solicita entrada no lobby por meio de JOIN.

Quando recebe WAITING, permanece aguardando START.

## 10. Controle da partida

Após receber START, o cliente armazena o identificador da partida, sua marca e o primeiro turno.

O tabuleiro inicial é recebido por BOARD.

As jogadas são enviadas por MOVE. O cliente aguarda MOVE_RESULT e utiliza BOARD para atualizar a representação do jogo.

Jogadas recusadas não alteram o tabuleiro apresentado.

Durante o turno adversário, o cliente aguarda as atualizações enviadas pelo servidor.

## 11. Encerramento e erros

O cliente apresenta os resultados recebidos em GAME_OVER:

- WIN: apresenta o vencedor.
- DRAW: apresenta empate.
- ABORTED: apresenta a interrupção da partida e seu motivo.

Também foram implementados tratamentos para falhas de conexão, erros de comunicação e respostas inesperadas.

Ao finalizar uma sessão, o cliente fecha a conexão.

## 12. Menu principal e execução

Foi implementado um menu de terminal com as opções:

1. Conectar e jogar.
2. Sair.

A execução utiliza:

`python -m client.client --host 127.0.0.1 --port 5000`

Os parâmetros `--host` e `--port` permitem configurar o endereço e a porta do servidor.

## 13. Testes realizados

Foram executados 29 testes específicos do cliente e 84 testes na suíte completa do projeto, todos aprovados.

Também foi realizado um teste manual com servidor TCP simulado na porta 5001, verificando conexão, identificação, entrada no lobby, início da partida, recebimento do tabuleiro, encerramento e retorno ao menu.

A implementação do servidor real não faz parte desta etapa. A comunicação foi validada com simulações.

## 14. Situação final

As etapas C01 a C13 foram desenvolvidas para a parte do cliente.

A aprovação conjunta do marco I01 permanece pendente de confirmação pela equipe.
