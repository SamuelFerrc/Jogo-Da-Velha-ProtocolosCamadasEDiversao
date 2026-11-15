# Jogo da Velha Multiplayer (UESC)

Jogo da velha 3×3 entre dois clientes conectados por **sockets TCP** a um servidor central, usando o protocolo de aplicação próprio **TTTP/1** (JSON por linha). Projeto acadêmico de comunicação cliente-servidor.

Requisitos: Python 3.11+ (somente biblioteca padrão).

## Como executar

Na raiz do repositório, em três terminais:

```bash
# Terminal 1 — servidor
python -m server.server --host 127.0.0.1 --port 5000

# Terminais 2 e 3 — clientes
python -m client.client --host 127.0.0.1 --port 5000
python -m client.client --host 127.0.0.1 --port 5000
```

O primeiro cliente a entrar aguarda; ao entrar o segundo, a partida começa (X joga primeiro).

## Testes

```bash
python -m unittest discover -s tests -v
```

## Documentação

- [Arquitetura](docs/arquitetura.md)
- [Protocolo TTTP/1](docs/protocolo.md)
- [Transporte](docs/transporte.md)
- [Servidor](docs/servidor.md)
- [Cliente](docs/cliente.md)
- [Máquinas de estados](docs/estados.md)
- [Linha do tempo de modificações](docs/linha_do_tempo.md)
