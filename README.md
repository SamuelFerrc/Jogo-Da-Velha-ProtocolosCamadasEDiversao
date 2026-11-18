# Jogo da Velha Multiplayer (UESC)

Jogo da velha 3×3 entre dois clientes conectados por **sockets TCP** a um servidor central, usando o protocolo de aplicação próprio **TTTP/1** (JSON por linha). Projeto acadêmico de comunicação cliente-servidor.

Requisitos: Python 3.11+ e PySide6 6.12 para as janelas Qt Quick/QML. A rede,
o protocolo e as regras continuam usando somente a biblioteca padrão.

Instale a dependência visual uma vez:

```bash
python -m pip install -r requirements.txt
```

## Como executar

Na raiz do repositório, em três terminais PowerShell/CMD:

```bash
# Terminal 1 — servidor
python -m server.server --host 127.0.0.1 --port 5000

# Terminais 2 e 3 — clientes
python -m client.client --host 127.0.0.1 --port 5000
python -m client.client --host 127.0.0.1 --port 5000
```

Quando o comando é executado em um terminal interativo, cada aplicação abre sua
janela gráfica e mantém no terminal um **espelho textual acionável** dos mesmos
estados e mensagens. A GUI PySide6/QML está isolada em `interface/`; cliente, servidor e
transporte continuam usando as implementações reais de `client/`, `server/` e
`shared/`.

O primeiro cliente a entrar aguarda; ao entrar o segundo, a partida começa (X joga primeiro).

Opções de apresentação:

```bash
# Preserva somente o fluxo textual anterior
python -m server.server --terminal-only
python -m client.client --terminal-only

# Força a janela mesmo quando stdout/stdin não são um terminal interativo
python -m server.server --gui
python -m client.client --gui
```

As janelas exibem, sem acrescentar campos à rede, a passagem real por
**aplicação → shared.transport → TCP → aplicação**, incluindo o objeto TTTP/1,
quantidade de bytes, framing JSONL/LF, buffer residual e decisão tomada pela
camada de aplicação.

Depois de vitória ou empate, o cliente pode enviar novo `JOIN` sem fechar a
conexão. Isso volta ao lobby para outra partida com novo `game_id`; o
pareamento é FIFO e pode selecionar outro adversário.

## Testes

```bash
python -m unittest discover -s tests -v
```

Na verificação de 2026-11-18, a suíte executou 151 testes com sucesso. A
integração automatizada cobre o servidor em processo separado e dois
participantes TCP. Ainda faltam, para a evidência final, executar duas
instâncias interativas do cliente na `main`, registrar as telas e salvar uma
captura `.pcapng` do tráfego TTTP/1.

## Documentação

- [Arquitetura](docs/arquitetura.md)
- [Protocolo TTTP/1](docs/protocolo.md)
- [Transporte](docs/transporte.md)
- [Servidor](docs/servidor.md)
- [Cliente](docs/cliente.md)
- [Máquinas de estados](docs/estados.md)
- [Interface gráfica e observabilidade](docs/interface_grafica.md)
- [Declaração de uso de inteligência artificial](docs/declaracao_uso_ia.md)
- [Linha do tempo de modificações](docs/linha_do_tempo.md)
