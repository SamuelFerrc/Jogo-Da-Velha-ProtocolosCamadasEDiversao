# Linha do tempo de modificações do projeto

Este histórico registra as modificações realizadas no repositório por agentes
de código. O objetivo é permitir que a equipe identifique o que mudou, por que
mudou, quais arquivos foram afetados e quais verificações sustentam cada
resultado.

Os horários usam o fuso **America/Bahia (UTC-03:00)**. Inspeções de leitura,
explicações em conversa e comandos que não alteram arquivos não constituem
modificações do repositório.

## Regras de registro

- Manter as entradas em ordem cronológica, da mais antiga para a mais recente.
- Registrar toda operação que crie, altere, remova ou renomeie arquivos.
- Uma entrada pode agrupar vários arquivos quando fazem parte da mesma mudança
  coordenada.
- Informar autor, tarefa ou objetivo, arquivos afetados, mudança, verificação e
  pendências.
- Não reescrever entradas antigas para ocultar ou substituir o histórico.
  Correções devem ser registradas em uma nova entrada que referencie a anterior.
- A atualização deste próprio arquivo faz parte da entrada da mudança que a
  motivou. Não criar uma segunda entrada apenas para registrar o registro.
- Não incluir segredos, credenciais, dados pessoais ou conteúdo sensível.

## Formato das próximas entradas

```text
### AAAA-MM-DD HH:MM — AUTOR — tarefa ou objetivo

- Arquivos: caminhos alterados.
- Modificação: descrição objetiva do estado anterior e do novo estado.
- Verificação: testes, inspeções e resultados efetivamente obtidos.
- Pendências: lacunas, aprovações ou verificações ainda necessárias.
```

## Histórico

### 2026-11-11 23:20 — CODEX — T01: contrato de comunicação

- Arquivos: `docs/protocolo.md`.
- Modificação: criado o contrato-base TTTP/1 com TCP, UTF-8, JSONL delimitado
  por LF, limite de 4096 bytes, envelope `type`/`version`, versionamento,
  regras gerais de envio e recepção e separação de responsabilidades.
- Verificação: sete verificações documentais confirmaram TCP, UTF-8, JSONL,
  limite, identificação, versão e separação do escopo de T02/T03. A linha T01
  da planilha foi conferida sem alteração do arquivo.
- Pendências: os arquivos de testes estavam vazios e o comando `unittest`
  executou zero testes. T01 permaneceu com status `Não iniciado` na planilha,
  aguardando revisão da equipe.

### 2026-11-11 23:34 — CODEX — T02 e T03: mensagens e erros

- Arquivos: `docs/protocolo.md`.
- Modificação: adicionados o catálogo dos 13 tipos TTTP/1, os esquemas JSON,
  a sequência nominal de eventos e o catálogo de 11 códigos de erro. Foi
  formalizada a separação entre `ERROR` para protocolo/sessão e
  `MOVE_RESULT(REJECTED)` para rejeição semântica de jogada.
- Verificação: 20 exemplos JSON foram decodificados com sucesso; todos possuíam
  `type` e `version: 1`; os 13 tipos e os 11 códigos estavam presentes; oito
  verificações de consistência passaram. As linhas T02 e T03 da planilha foram
  conferidas sem alteração do arquivo.
- Pendências: os arquivos de testes continuavam vazios e o comando `unittest`
  executou zero testes. T02 e T03 permaneceram com status `Não iniciado` na
  planilha. O marco I01 ainda dependia de C01, S01 e aprovação conjunta.

### 2026-11-11 23:35 — CODEX — governança do histórico de modificações

- Arquivos: `docs/linha_do_tempo.md` e `AGENTS.md`.
- Modificação: criada esta linha do tempo com o histórico das alterações feitas
  pelo CODEX e adicionada ao `AGENTS.md` a obrigação de registrar toda futura
  criação, alteração, remoção ou renomeação de arquivo.
- Verificação: conferência da existência do documento, da seção obrigatória no
  `AGENTS.md`, do modelo de entrada e do item correspondente no checklist de
  entrega.
- Pendências: nenhuma modificação de código foi realizada nesta etapa.

### 2026-11-11 23:49 — CODEX — T04, T05 e T06: base TCP

- Arquivos: `shared/protocol.py`, `shared/transport.py`,
  `tests/test_protocol.py`, `tests/test_transport.py` e
  `docs/linha_do_tempo.md`.
- Modificação: implementadas as constantes e primitivas JSONL do TTTP/1, a
  abertura de conexão cliente, criação de socket de escuta, aceitação de
  conexões, fechamento idempotente, envio com `sendall()` e lock por conexão,
  recepção com buffer persistente, reconstrução de registros fragmentados,
  separação de registros concatenados e exceções controladas para EOF, timeout,
  tamanho excessivo e falhas de socket. Os wrappers de socket bruto reutilizam
  o mesmo canal para não perder bytes residuais.
- Verificação: `python -m unittest discover -s tests -v` executou 29 testes com
  sucesso. Foram cobertos UTF-8, LF, limite exato de 4096 bytes, rejeição acima
  do limite, JSON inválido, versão inválida, fragmentação, concatenação, EOF,
  timeouts, erros de socket, fechamento idempotente, loopback TCP real e oito
  envios concorrentes sem intercalação. `python -m compileall -q shared tests`
  terminou sem erros.
- Pendências: a validação completa dos payloads permanece em T07. A
  documentação detalhada de transporte permanece em T13. A planilha de etapas
  não foi alterada.

### 2026-11-12 00:21 — CODEX — T07, T08, T09 e T10: protocolo e resiliência

- Arquivos: `shared/__init__.py`, `shared/protocol.py`,
  `shared/transport.py`, `tests/test_protocol.py`,
  `tests/test_transport.py` e `docs/linha_do_tempo.md`.
- Modificação: implementada a validação estrutural completa dos 13 tipos
  TTTP/1, incluindo campos exatos, tipos, enumerações, matriz 3×3, variantes
  condicionais, códigos de erro separados e detecção de campos JSON duplicados.
  A API estável foi exportada por `shared`. Canais agora fecham em EOF e falha
  irrecuperável de socket, preservam buffer parcial em timeout de recepção e
  permitem configurar ou remover timeout local. O heartbeat opcional fornece
  `send_ping()` e `handle_heartbeat_message()`, respondendo `PONG` sem alterar
  estados do jogo.
- Verificação: `python -m unittest discover -s tests -v` executou 49 testes com
  sucesso. Foram validados os exemplos canônicos, campos ausentes ou extras,
  booleanos e tipos incorretos, direções cliente/servidor, códigos incompatíveis,
  tabuleiros inválidos, API pública, recuperação após timeout parcial, fechamento
  em EOF/falhas e o fluxo PING/PONG. `python -m compileall -q shared tests`
  terminou sem erros, e a API pública expôs 36 nomes.
- Pendências: a periodicidade do heartbeat e sua ativação pertencem aos loops de
  cliente e servidor, ainda não implementados. A planilha de etapas não foi
  alterada e a documentação detalhada de transporte permanece em T13.

### 2026-11-12 00:26 — CODEX — T11, T12 e T13: testes, tráfego e documentação

- Arquivos: `shared/protocol.py`, `tools/__init__.py`,
  `tools/traffic_demo.py`, `tests/test_transport.py`,
  `tests/test_integration.py`, `docs/protocolo.md`, `docs/transporte.md` e
  `docs/linha_do_tempo.md`.
- Modificação: adicionados testes com sockets reais para fragmentação,
  concatenação, Unicode e registros inválidos; criado um gerador reproduzível
  de tráfego TCP com `HELLO/WELCOME`, `PING/PONG` e `QUIT`; documentados a
  justificativa do TCP, JSONL, buffer, locks, limites, EOF, timeout, API,
  exceções, heartbeat, sequência de eventos, erros, execução dos testes e o
  procedimento de inspeção no Wireshark. As descrições internas de
  `shared/protocol.py` foram atualizadas para refletir a validação completa já
  implementada. A planilha foi consultada em modo somente leitura para conferir
  os critérios de T11–T13 e não foi alterada.
- Verificação: `python -m unittest discover -s tests -v` executou 55 testes com
  sucesso. `python -m compileall -q shared tests tools` terminou sem erros.
  `python -m tools.traffic_demo --port 0 --delay 0` concluiu a troca prevista
  sobre uma conexão TCP real. Uma inspeção documental confirmou a presença dos
  tópicos exigidos pela planilha: TCP, enquadramento, timeout, JSON, sequência,
  erros e limites de visibilidade da captura.
- Pendências: T12 ainda requer uma captura visual real e o arquivo de evidência
  `.pcapng`. Wireshark, TShark e dumpcap não estavam instalados neste ambiente;
  o PktMon estava disponível, mas seu driver negou acesso. Nenhuma captura foi
  declarada como concluída. A planilha permanece com os status originais.

### 2026-11-12 01:16 — CODEX — versionamento inicial no Git

- Arquivos: `.gitignore` e `docs/linha_do_tempo.md`.
- Modificação: inicializado o repositório Git local na branch `main`, configurado
  `origin` para o repositório solicitado no GitHub e criado `.gitignore` para
  impedir o versionamento de bytecode, caches, ambientes virtuais, arquivos de
  ambiente e metadados locais de editores/sistema operacional. Nenhum contrato
  TTTP/1 nem comportamento de cliente ou servidor foi alterado.
- Verificação: o repositório remoto foi consultado e não possuía branches ou
  tags; `python -m unittest discover -s tests -v` executou 55 testes com sucesso;
  `python -m compileall -q shared client server tests tools` terminou sem erros;
  `git check-ignore` confirmou que caches de `shared/` e `tests/` são ignorados.
- Pendências: a publicação remota será verificada após a criação do primeiro
  commit. Permanecem as lacunas funcionais e de evidência já registradas nas
  entradas anteriores; este versionamento não as declara concluídas.

### 2026-11-12 21:30 — USUÁRIO — C01: especificação do fluxo do cliente

- Arquivos: `docs/cliente.md` e `docs/linha_do_tempo.md`.
- Modificação: preenchido `docs/cliente.md` com a jornada do jogador, menu inicial de terminal, fluxo de conexão, identificação, lobby, partida, jogadas, resultados, encerramento e casos de uso.
- Verificação: conteúdo salvo e conferido pelo usuário por meio do comando `type docs\cliente.md`.
- Pendências: validação da especificação pela equipe e aprovação conjunta do marco I01. Implementação do cliente ainda não iniciada.


### 2026-11-13 00:06 — USUÁRIO — C02 a C13: implementação e documentação do cliente

- Arquivos: `client/interface.py`, `client/client.py`, `tests/test_client.py`, `testar_lobby.py`, `docs/cliente.md` e `docs/linha_do_tempo.md`(Sendo alguns apwnas para testes).
- Modificação: implementada a interface de terminal com tabuleiro 3×3 e entrada de coordenadas. Desenvolvidas as funções de conexão TCP, identificação, entrada e espera no lobby, início da partida, envio de jogadas, processamento de resultados, atualização do tabuleiro, recebimento das jogadas do adversário e encerramento. Adicionado o menu principal com as opções de conectar e jogar ou sair, além dos argumentos `--host` e `--port`. Criados testes automatizados para o cliente e atualizada a documentação com as etapas C02 a C13.
- Verificação: `python -m py_compile client\client.py` executado sem erros. Testados manualmente o menu e a opção de saída. Realizado teste com servidor TCP simulado na porta 5001, verificando conexão, identificação, entrada no lobby, início da partida, recebimento do tabuleiro, encerramento e retorno ao menu. Os 29 testes específicos do cliente passaram. A suíte completa executou 84 testes, todos aprovados.
- Pendências: integração com o servidor real não realizada, pois sua implementação não faz parte desta responsabilidade. A aprovação conjunta do marco I01 permanece pendente da equipe. A entrada anterior de C01 registrava a implementação como ainda não iniciada; esta entrada complementa e atualiza aquele registro.

### 2026-11-13 01:40 — USUÁRIO — revanche no servidor de teste local

- Arquivos: `client/client.py`, `servidor_teste.py`, `docs/cliente.md` e `docs/linha_do_tempo.md`.
- Modificação: após vitória ou empate, o cliente pergunta se deseja jogar novamente e mantém a conexão TCP aberta. O servidor de teste aguarda a decisão dos dois clientes; se ambos aceitarem, inicia outra partida, reinicia o tabuleiro e alterna as marcas. Se alguém recusar, encerra a sessão; se o outro tiver aceitado, informa que a revanche foi cancelada.
- Verificação: não executada nesta etapa. Para validar manualmente, inicie `python servidor_teste.py` e conecte os dois clientes com `python -m client.client`; conclua uma partida e responda `s` nos dois clientes.
- Limitação: esta alteração é para `servidor_teste.py`. O servidor oficial em `server/server.py` ainda não foi adaptado para a revanche.

### 2026-11-13 19:20 —  USUÁRIO — validações TTTP/1 e placar entre revanches

- Arquivos: `client/client.py`, `servidor_teste.py`, `docs/protocolo.md`, `docs/cliente.md` e `docs/linha_do_tempo.md`.
- Modificação: o cliente confere `game_id`, revisões consecutivas, correspondência entre `MOVE_RESULT` e a jogada, alteração de uma única célula e consistência entre o tabuleiro terminal e `GAME_OVER`. O placar temporário acompanha vitórias do jogador local, do adversário e empates durante a sequência de revanches; não é persistido. O contrato documenta `JOIN` como pedido de revanche após `GAME_OVER(WIN|DRAW)`, `QUIT` como recusa e o uso de um novo `game_id` para cada partida. O servidor de teste encerra a sessão quando qualquer um recusa, sem emitir `GAME_OVER` para uma partida que não começou.
- Verificação: não executada nesta etapa.
- Limitação: a implementação do placar e da revanche permanece no cliente e no servidor de teste. Os arquivos do servidor oficial continuam sem implementação.

### 2026-11-14 01:35 — USUÁRIO — atualização dos testes do cliente

- Arquivos: `tests/test_client.py` e `docs/linha_do_tempo.md`.
- Modificação: atualizadas as simulações de partidas para incluir `game_id`, `revision`, coordenadas confirmadas e `GAME_OVER`. Acrescentada cobertura para snapshots de partida, progressão da revisão, correspondência de jogadas, validação de vitória/empate, placar por jogador e aceitação/recusa de revanche.
- Verificação: testes não executados nesta etapa.
### 2026-11-15 11:35 — Guilherme Crocamo — S07–S09: regras puras da partida

- Arquivos: `server/game.py`, `tests/test_game.py` e `docs/linha_do_tempo.md`.
- Modificação: `server/game.py` estava vazio. Agora implementa `Game`
  (estado autoritativo com lock reentrante), `Snapshot`, `MoveOutcome`,
  `find_winner` (3 linhas, 3 colunas, 2 diagonais) e `is_full`, sem sockets.
  A ordem de validação é participação/`game_id`, partida ativa, turno, posição
  e célula ocupada; rejeições não alteram tabuleiro, turno nem `revision`.
- Verificação: `python -m unittest tests.test_game` executou 13 testes com
  sucesso (vitória X/O, empate, rejeições, coordenadas booleanas/fracionárias,
  jogada após término/aborto e dois `MOVE` concorrentes).
- Pendências: lobby, servidor TCP e testes de integração nas próximas entradas.

### 2026-11-15 11:45 — Guilherme Crocamo — S04–S06: lobby e pareamento

- Arquivos: `server/lobby.py`, `tests/test_lobby.py` e `docs/linha_do_tempo.md`.
- Modificação: `server/lobby.py` estava vazio. Agora implementa `Lobby`, fila
  FIFO com lock: o primeiro da fila recebe X, `game_id` sequencial único
  (`g1`, `g2`, ...), descarte de sessões desconectadas, `remove` e entrada
  duplicada idempotente. `tests/test_lobby.py` foi criado (não constava na
  estrutura prevista; separa o lobby de `test_server.py`).
- Verificação: `python -m unittest tests.test_lobby` executou 5 testes com
  sucesso, incluindo 20 `join` concorrentes formando 10 pares sem repetição.
- Pendências: integração do lobby ao servidor TCP na próxima entrada.

### 2026-11-15 11:58 — Guilherme Crocamo — S14: cobertura adicional de testes do servidor

- Arquivos: `tests/test_server.py` e `docs/linha_do_tempo.md`.
- Modificação: adicionados testes com sockets de loopback para vitória de X em
  coluna, vitória de X na diagonal principal, vitória de O na diagonal
  secundária e encerramento das conexões quando o servidor é parado. Nenhum
  código de produção foi alterado.
- Verificação: `python -m unittest discover -s tests` executou 105 testes com
  sucesso em 3 execuções consecutivas.
- Pendências: captura Wireshark (T12), teste em outra máquina da rede,
  integração com o cliente após o merge do PR do cliente e harmonização do
  PDF/planilha. Push e PR ainda não realizados, por decisão da equipe.

### 2026-11-15 12:20 — Guilherme Crocamo — S02–S03, S05–S14: servidor TCP

- Arquivos: `server/server.py`, `tests/test_server.py` e `docs/linha_do_tempo.md`.
- Modificação: `server/server.py` estava vazio. Agora implementa `GameServer`
  (`listen/accept`, uma thread de leitura e uma de escrita por conexão, fila de
  saída por sessão enfileirada sob o lock da partida para preservar a ordem
  `MOVE_RESULT` → `BOARD` → `GAME_OVER`), a máquina de estados da sessão
  (CONECTADO → IDENTIFICADO → AGUARDANDO → EM_PARTIDA → ENCERRADO), tratamento
  de `BAD_FORMAT`, `UNKNOWN_TYPE`, `UNSUPPORTED_VERSION` (fecha),
  `MESSAGE_TOO_LARGE` (fecha), `INVALID_STATE`, rejeições semânticas via
  `MOVE_RESULT(REJECTED)`, `GAME_OVER(ABORTED)` em QUIT/EOF, timeout apenas de
  handshake, `PING`→`PONG` e CLI `python -m server.server --host --port`.
  Decisão registrada: `JOIN` também é aceito no estado ENCERRADO para a
  revanche descrita em `docs/cliente.md` da branch do cliente (nova partida,
  novo `game_id`); isso estende o diagrama de estados de AGENTS.md §6.1 e deve
  ser harmonizado na documentação.
- Verificação: `python -m unittest discover -s tests` executou 100 testes com
  sucesso em 3 execuções consecutivas (27 em `test_server.py`: handshake,
  lobby, erros de protocolo, fragmentação/concatenação, vitórias X/O, empate,
  rejeições sem mutação, MOVE concorrentes, QUIT/queda de socket, revanche).
- Pendências: integração com o cliente real depende do merge do PR do cliente;
  documentação do servidor e README nas próximas entradas.

### 2026-11-15 12:40 — Guilherme Crocamo — I03–I05: integração com servidor em processo separado

- Arquivos: `tests/test_integration.py` e `docs/linha_do_tempo.md`.
- Modificação: adicionado `ServerProcessTests`, que inicia
  `python -m server.server` como subprocesso e conduz uma partida completa
  (HELLO/WELCOME, JOIN/WAITING, START, BOARD inicial, vitória de X e
  `GAME_OVER` para ambos) por TCP de loopback.
- Verificação: `python -m unittest discover -s tests` executou 101 testes com
  sucesso. Verificação manual extra, fora do repositório: o cliente real da
  branch `origin/Gust4vo73-patch-1` (extraído via `git archive` para uma pasta
  temporária) jogou duas instâncias contra o servidor, com vitória de X exibida
  corretamente e recusa de revanche encerrando as sessões. Não foi executado o
  cenário de revanche aceita com o cliente real.
- Pendências: repetir com o cliente já mergeado na `main`; captura Wireshark
  (T12) segue pendente.

### 2026-11-15 12:55 — Guilherme Crocamo — S15 / I08: documentação do servidor

- Arquivos: `README.md`, `docs/servidor.md`, `docs/estados.md`,
  `docs/arquitetura.md` e `docs/linha_do_tempo.md`.
- Modificação: os quatro primeiros estavam vazios. Agora descrevem execução
  (servidor e dois clientes a partir da raiz), módulos, concorrência e ordem de
  locks, tratamento de cada erro, desconexões, máquinas de estados da sessão e
  da partida, sequência de jogada e arquitetura geral.
- Divergência registrada para harmonização com o PDF/planilha: a revanche via
  `JOIN` no estado ENCERRADO (exigida pelo cliente) não consta no diagrama de
  AGENTS.md §6.1.
- Verificação: documentação conferida contra o código e contra os 101 testes
  executados na entrada anterior; não houve alteração de código nesta entrada.
  `README.md` e `docs/servidor.md` referenciam `docs/cliente.md`, que só existe
  após o merge do PR do cliente.
- Pendências: captura Wireshark (T12); atualizar PDF e planilha.

### 2026-11-18 00:58 — CODEX — harmonização documental e status do plano

- Arquivos: `AGENTS.md`, `README.md`,
  `Plano_Etapas_Jogo_da_Velha_UESC.xlsx`, `docs/arquitetura.md`,
  `docs/cliente.md`, `docs/estados.md`, `docs/protocolo.md`,
  `docs/servidor.md`, `docs/transporte.md` e
  `docs/linha_do_tempo.md`.
- Modificação: a documentação ainda descrevia a nova partida na mesma conexão
  como revanche bilateral e mantinha contagens e status anteriores à
  integração. O fluxo foi harmonizado com o código: `JOIN` após
  `GAME_OVER` retorna a sessão ao lobby, sempre cria outro `game_id` e não
  garante o mesmo adversário. Foram atualizados os diagramas, a sequência
  TTTP/1, as limitações, a cobertura de testes e os critérios pendentes. A
  planilha passou de 49 itens como `Não iniciado` para 44 `Concluído` e 5
  `Em andamento` (T12, C13, I01, I04 e I08), com evidências nos marcos de
  integração. Também foram corrigidos na planilha o intervalo 1..3 da
  interface com conversão para 0..2, a rejeição semântica por
  `MOVE_RESULT(REJECTED)`, o catálogo PING/PONG e o ciclo de estados.
- Verificação: `python -m unittest discover -s tests -v` executou 141 testes
  com sucesso; `python -m compileall -q shared client server tests tools`
  terminou sem erros; `git -c core.whitespace=cr-at-eol diff --check` não
  encontrou erros. A planilha foi recalculada, reimportada e renderizada nas
  cinco abas; o resumo resultou em 44 concluídos, 5 em andamento e 90% de
  progresso arredondado, sem erros de fórmula detectados.
- Pendências: registrar a aprovação formal do I01; executar a demonstração da
  `main` com servidor e dois clientes interativos em processos distintos;
  produzir as capturas de tela de C13 e a captura Wireshark `.pcapng` de
  T12/I08. O PDF de referência não foi alterado por não haver neste
  repositório uma fonte editável correspondente; ele pode continuar sem a
  extensão de novo `JOIN` após `GAME_OVER`.

### 2026-11-18 01:43 — CODEX — interfaces gráficas e visualização das camadas

- Arquivos criados: `design/DESIGN-coinbase.md`,
  `design/auditoria-ihc-nielsen-shneiderman/README.md`,
  `design/auditoria-ihc-nielsen-shneiderman/SKILL.md`,
  `design/auditoria-ihc-nielsen-shneiderman/assets/modelo-relatorio.md`,
  `design/auditoria-ihc-nielsen-shneiderman/examples/self-checkout.md`,
  `design/auditoria-ihc-nielsen-shneiderman/references/principios.md`,
  `interface/__init__.py`, `interface/client_state.py`,
  `interface/client_window.py`, `interface/server_window.py`,
  `interface/theme.py`, `interface/widgets.py`, `shared/telemetry.py`,
  `tests/test_interface.py` e `docs/interface_grafica.md`.
- Arquivos alterados: `client/client.py`, `server/server.py`,
  `shared/transport.py`, `README.md`, `docs/arquitetura.md`,
  `docs/cliente.md`, `docs/servidor.md`, `docs/transporte.md` e
  `docs/linha_do_tempo.md`.
- Modificação: antes, cliente e servidor possuíam somente apresentação textual
  e o transporte não expunha observabilidade. Foram adicionadas janelas
  Tkinter na pasta isolada `interface/`, abertas automaticamente pelos mesmos
  comandos quando executados em PowerShell/CMD interativo, com espelho textual
  acionável e opções `--gui`/`--terminal-only`. Cliente e servidor exibem a
  passagem real por aplicação, `shared.transport` e TCP, sem modificar TTTP/1.
  `MessageChannel` ganhou telemetria opcional e tolerante a falhas; o servidor
  expõe uma fotografia somente de leitura das sessões. O visual foi revisto
  conforme `design/DESIGN-coinbase.md`: azul único, hero escuro, canvas branco,
  tipografia editorial, cartões de 24 px, campos de 12 px, botões e badges
  pill, uma sombra e cartões APP/TCP sobrepostos. Os princípios de Nielsen e
  Shneiderman da pasta `design/` orientaram feedback, prevenção de erros,
  reconhecimento, teclado e encerramento claro.
- Verificação: `python -m unittest discover -s tests -v` executou 148 testes
  com sucesso; `python -m compileall -q shared client server interface tests`
  terminou sem erros. Tkinter 8.6 foi importado e as janelas de servidor e
  cliente foram iniciadas localmente; uma inspeção anterior identificou e
  motivou a correção da largura do painel do cliente. A captura automatizada
  do visual final redesenhado não foi concluída porque outra janela permaneceu
  em primeiro plano; os processos de validação foram encerrados depois do
  teste.
- Pendências: executar uma partida completa usando duas janelas e o espelho de
  terminal; produzir as capturas finais de C13; salvar a captura Wireshark
  `.pcapng` de T12/I08; validar o layout final em tela menor e com tecnologia
  assistiva. A aprovação formal de I01 continua externa a esta mudança.

### 2026-11-18 02:03 — CODEX — aplicação dos esboços aprovados nas duas telas

- Arquivos alterados: `interface/theme.py`, `interface/widgets.py`,
  `interface/client_window.py`, `interface/server_window.py`,
  `server/server.py`, `tests/test_interface.py`,
  `docs/interface_grafica.md` e `docs/linha_do_tempo.md`.
- Modificação: a primeira interface gráfica renderizada usava cartões com
  geometria inconsistente e dava mais destaque ao terminal que ao jogo. O
  cliente agora replica o esboço aprovado: tabuleiro quadrado como área
  principal, coluna secundária de conexão/sessão, estado autoritativo e
  terminal TTTP/1 em gaveta inferior sobreposta e recolhida por padrão. A
  conexão começa automaticamente com o host/porta da linha de comando. O
  servidor agora replica o esboço de central de partidas, com resumo superior,
  sessões à esquerda e fluxo de aplicação/transporte à direita. Cartões,
  botões, badges, cores e hierarquia foram ajustados aos tokens de
  `design/DESIGN-coinbase.md`. `status_snapshot()` passou a fornecer também
  resumo somente de leitura de cada partida para o painel, sem alterar TTTP/1.
- Verificação: `python -m unittest discover -s tests -v` executou 149 testes
  com sucesso; `python -m compileall -q shared client server interface tests`
  terminou sem erros e `git -c core.whitespace=cr-at-eol diff --check` não
  encontrou erro de whitespace. Cliente e
  servidor foram iniciados como três processos reais (um servidor e dois
  clientes), parearam em `g1` e as duas janelas finais foram capturadas por
  processo para inspeção visual. A captura confirmou tabuleiro quadrado,
  terminal recolhido, duas sessões no servidor e fluxo TTTP/1 real.
- Pendências: validar interação de arrasto e teclado com tecnologia assistiva;
  produzir a captura Wireshark `.pcapng` de T12/I08. A aprovação
  formal de I01 continua externa a esta mudança.

### 2026-11-18 02:20 — CODEX — migração para PySide6/QML e gaveta que comprime o cliente

- Arquivos criados: `requirements.txt`, `interface/qt_common.py`,
  `interface/qml/ClientWindow.qml`, `interface/qml/ServerWindow.qml`,
  `interface/qml/components/DesignTokens.qml`,
  `interface/qml/components/LayerStrip.qml`,
  `interface/qml/components/PillBadge.qml`,
  `interface/qml/components/PillButton.qml`,
  `interface/qml/components/TraceTerminal.qml` e
  `tests/test_qt_interface.py`.
- Arquivos alterados: `interface/client_window.py`,
  `interface/server_window.py`, `README.md`, `docs/arquitetura.md`,
  `docs/cliente.md`, `docs/interface_grafica.md` e
  `docs/linha_do_tempo.md`. Arquivos removidos:
  `interface/theme.py` e `interface/widgets.py`.
- Modificação: a camada visual Tkinter foi substituída por backends PySide6 e
  telas Qt Quick/QML, mantendo os mesmos controladores de rede, o protocolo
  TTTP/1, o `GameServer`, os comandos de PowerShell/CMD e o espelho textual.
  As telas de cliente e servidor aplicam a composição dos esboços e os tokens
  de `design/DESIGN-coinbase.md`. No cliente, o terminal deixou de se sobrepor
  à interface: a altura animada da gaveta agora redefine o limite inferior da
  área principal. O tabuleiro reduz uniformemente e permanece quadrado, com
  células proporcionais, durante clique ou arrasto. A abertura dura 340 ms e
  o fechamento 250 ms.
- Verificação: `python -m unittest discover -s tests -v` executou 151 testes
  com sucesso, incluindo dois testes Qt/QML fora de tela para carregamento das
  janelas, inicialização do servidor, contração do layout e proporção 1:1 do
  tabuleiro. `python -m compileall -q shared client server interface tests`
  terminou sem erros e `git -c core.whitespace=cr-at-eol diff --check` não
  encontrou erros. Um servidor e clientes reais foram iniciados na porta
  5000; a captura da janela maximizada confirmou a gaveta aberta abaixo da
  interface, a área principal comprimida e o tabuleiro sem deformação.
- Pendências: validar a navegação completa com tecnologia assistiva; produzir
  a captura Wireshark `.pcapng` de T12/I08. A aprovação formal de I01 continua
  externa a esta mudança.

### 2026-11-18 02:46 — CODEX — correções documentais e declaração de uso de IA

- Arquivo criado: `docs/declaracao_uso_ia.md`.
- Arquivos alterados: `README.md`, `docs/cliente.md`,
  `docs/linha_do_tempo.md`, `Plano_Etapas_Jogo_da_Velha_UESC.xlsx` e
  `Projeto_Jogo_da_Velha_Cliente_Servidor_UESC_ABNT.pdf`.
- Modificação: a documentação do cliente passou a distinguir as coordenadas de
  interface 1..3 dos índices 0..2 do protocolo. A entrada de 11:58 foi movida
  para sua posição cronológica e a entrada das interfaces passou a enumerar os
  arquivos criados em `design/`. A atividade T03 da planilha agora lista o
  catálogo completo de onze códigos de erro. Foi criada uma declaração pública
  do uso de OpenAI Codex e adicionado seu link ao README. Como o PDF não possui
  fonte editável no repositório, suas treze páginas originais foram preservadas
  e uma página normativa de harmonização foi inserida após a capa, com os
  exemplos TTTP/1 corretos, o fluxo de nova partida e a declaração resumida de
  uso de IA.
- Verificação: `python -m unittest discover -s tests -v` executou 151 testes
  com sucesso; `python -m compileall -q shared client server interface tests
  tools` terminou sem erros; `git -c core.whitespace=cr-at-eol diff --check`
  não encontrou erros. A planilha foi recalculada, exportada, reaberta e
  renderizada; T03 contém os onze códigos e a busca de erros de fórmula não
  encontrou ocorrências. O PDF foi reaberto com 14 páginas, teve a nova página
  e as páginas adjacentes renderizadas sem cortes ou sobreposições e contém os
  termos normativos esperados. Os 22 links locais da documentação foram
  verificados, sem destinos ausentes, e as 23 entradas reais da linha do tempo
  ficaram em ordem cronológica.
- Pendências: permanecem as pendências anteriores de evidência final, incluindo
  a captura Wireshark de T12/I08, as capturas exigidas por C13 e a aprovação
  formal de I01. Se a fonte editável do PDF for recuperada, a nota normativa
  pode ser incorporada diretamente ao corpo e ao sumário em uma futura edição.

### 2026-11-19 00:43 — CODEX — README como documentação principal da entrega

- Arquivos alterados: `README.md` e `docs/linha_do_tempo.md`.
- Modificação: o README anterior apresentava a execução e encaminhava o leitor
  aos documentos separados, mas não reunia sozinho todos os itens solicitados
  no enunciado. O novo README passou a ser uma documentação autocontida com
  propósito, funcionamento, arquitetura, justificativa do TCP, requisitos
  mínimos, execução local e em LAN, formato TTTP/1, catálogo completo de
  mensagens, ordem dos eventos, máquinas de estados, erros, invariantes,
  desconexões, estrutura e testes. As referências para `docs/` foram mantidas
  como aprofundamento técnico, sem substituir o conteúdo principal.
- Verificação: `python -m unittest discover -s tests -v` executou 151 testes
  com sucesso. Uma verificação dos links Markdown encontrou 11 referências com
  destinos locais existentes; a checagem das dez seções exigidas no README não
  encontrou ausência; `git -c core.whitespace=cr-at-eol diff --check` não
  encontrou erro de whitespace.
- Pendências: a configuração documentada para LAN não foi exercitada entre
  máquinas físicas nesta mudança. Permanecem pendentes a captura Wireshark
  `.pcapng` de T12/I08, as evidências finais exigidas por C13 e a aprovação
  formal externa de I01.

### 2026-11-19 01:14 — CODEX — atualização ao vivo do painel do servidor

- Arquivos alterados: `interface/server_window.py`,
  `interface/qml/ServerWindow.qml`, `tests/test_qt_interface.py`, `README.md` e
  `docs/linha_do_tempo.md`.
- Modificação: o temporizador de fotografia do servidor era iniciado no
  construtor de `ServerBackend`, antes de existir uma `QGuiApplication` na
  inicialização real pela linha de comando. O Qt não ativava esse temporizador;
  o jogo e as conexões continuavam funcionando, mas o painel permanecia em
  “Aguardando conexões TCP” e “Nenhuma partida ativa”. O temporizador agora é
  iniciado junto com `startServer()` e interrompido com `stopServer()`. A lista
  de sessões e o resumo de partida receberam identificadores somente para
  inspeção automatizada. O teste Qt passou a conectar dois canais TCP reais,
  executar `HELLO`/`JOIN`, formar `g1` e confirmar na interface duas sessões e
  uma partida ativa. O total documentado da suíte foi atualizado para 152.
- Verificação: `python -m unittest tests.test_qt_interface -v` executou 3
  testes com sucesso; `python -m unittest discover -s tests -v` executou 152
  testes com sucesso; `python -m compileall -q interface tests` terminou sem
  erros; `git -c core.whitespace=cr-at-eol diff --check` não encontrou erro de
  whitespace.
- Pendências: a correção foi validada com Qt em modo offscreen e dois sockets
  TCP de loopback. A confirmação visual em outra máquina/LAN continua sendo
  uma verificação manual recomendada; permanecem também as evidências finais
  já registradas para T12/I08, C13 e I01.
