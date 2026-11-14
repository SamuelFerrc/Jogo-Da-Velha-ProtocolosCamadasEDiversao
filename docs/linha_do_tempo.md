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
