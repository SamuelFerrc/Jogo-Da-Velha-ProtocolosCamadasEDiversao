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
