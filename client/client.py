
import argparse

from shared.transport import (
    connect_to_server,
    close_connection,
    TransportError
)

from shared.protocol import make_message, ProtocolError

from client.interface import (
    exibir_tabuleiro,
    solicitar_jogada
)


def conectar_servidor(host="127.0.0.1", porta=5000):
    """Estabelece conexão TCP com o servidor."""

    print(f"Conectando ao servidor {host}:{porta}...")

    try:
        conexao = connect_to_server(host, porta)
        print("Conexão estabelecida com sucesso!")
        return conexao

    except TransportError as erro:
        print(f"Não foi possível conectar: {erro}")
        return None


def entrar_no_lobby(conexao):
    """Identifica o cliente e solicita entrada no lobby."""

    try:
        conexao.send_message(make_message("HELLO"))
        print("Identificação enviada ao servidor.")

        resposta = conexao.receive_message()

        if resposta["type"] == "ERROR":
            print("Erro do servidor:", resposta["message"])
            return None

        if resposta["type"] != "WELCOME":
            print("Resposta inesperada do servidor:", resposta["type"])
            return None

        print("Cliente identificado com sucesso!")

        conexao.send_message(make_message("JOIN"))
        print("Solicitação para entrar no lobby enviada.")

        resposta = conexao.receive_message()

        if resposta["type"] == "WAITING":
            print("Aguardando outro jogador...")
            return aguardar_inicio_partida(conexao, resposta)

        if resposta["type"] == "START":
            print("Partida iniciada!")
            return resposta

        if resposta["type"] == "ERROR":
            print("Erro do servidor:", resposta["message"])
            return None

        print("Resposta inesperada:", resposta["type"])
        return None

    except (TransportError, ProtocolError) as erro:
        print(f"Falha na comunicação: {erro}")
        return None

def aguardar_inicio_partida(conexao, resposta_lobby):
    """Aguarda o servidor iniciar a partida após o WAITING."""

    if resposta_lobby["type"] == "START":
        print("Partida iniciada!")
        return resposta_lobby

    if resposta_lobby["type"] != "WAITING":
        print("Não foi possível aguardar a partida.")
        return None

    print("Aguardando outro jogador...")

    try:
        while True:
            resposta = conexao.receive_message()

            if resposta["type"] == "START":
                print("Partida iniciada!")
                return resposta

            if resposta["type"] == "ERROR":
                print("Erro do servidor:", resposta["message"])
                return None

            print("Resposta inesperada:", resposta["type"])
            return None

    except (TransportError, ProtocolError) as erro:
        print("Falha ao aguardar partida:", erro)
        return None


def iniciar_partida(conexao, resposta_start):
    """Recebe os dados iniciais da partida e o primeiro tabuleiro."""

    if resposta_start["type"] != "START":
        print("Resposta inesperada. Esperava START.")
        return None

    game_id = resposta_start["game_id"]
    marca = resposta_start["mark"]
    primeiro_turno = resposta_start["first_turn"]

    if not game_id or primeiro_turno != "X" or marca not in {"X", "O"}:
        print("START inconsistente com o protocolo TTTP/1.")
        return None

    print("\n=== PARTIDA INICIADA ===")
    print("ID da partida:", game_id)
    print("Sua marca:", marca)
    print("Primeiro turno:", primeiro_turno)

    try:
        resposta = conexao.receive_message()

        if resposta["type"] != "BOARD":
            print("Esperava BOARD, mas recebeu:", resposta["type"])
            return None

        if (
            resposta["game_id"] != game_id
            or resposta["revision"] != 0
            or resposta["turn"] != primeiro_turno
            or any(celula for linha in resposta["board"] for celula in linha)
        ):
            print("BOARD inicial inconsistente com START ou TTTP/1.")
            return None

        print("\nTabuleiro recebido do servidor:")
        exibir_tabuleiro(resposta["board"])

        return resposta

    except (TransportError, ProtocolError) as erro:
        print("Erro ao receber o tabuleiro:", erro)
        return None


def enviar_jogada(conexao, game_id, linha, coluna):
    """Envia uma jogada ao servidor."""

    if linha not in range(3) or coluna not in range(3):
        print("Coordenadas inválidas!")
        return False

    try:
        mensagem = make_message(
            "MOVE",
            game_id=game_id,
            row=linha,
            col=coluna
        )

        conexao.send_message(mensagem)

        print(
            f"Jogada enviada ao servidor: "
            f"linha {linha}, coluna {coluna}"
        )

        return True

    except (TransportError, ProtocolError) as erro:
        print("Erro ao enviar jogada:", erro)
        return False


def processar_resultado_jogada(conexao, tabuleiro_atual):
    """Processa o resultado da jogada enviado pelo servidor."""

    try:
        resultado = conexao.receive_message()

        if resultado["type"] != "MOVE_RESULT":
            print("Resposta inesperada:", resultado["type"])
            return tabuleiro_atual

        if resultado["status"] == "REJECTED":
            print("\nJogada recusada pelo servidor.")
            print("Motivo:", resultado["message"])

            return tabuleiro_atual

        if resultado["status"] == "ACCEPTED":
            print("\nJogada aceita pelo servidor!")

            resposta = conexao.receive_message()

            if resposta["type"] != "BOARD":
                print("Esperava BOARD, mas recebeu:", resposta["type"])
                return tabuleiro_atual

            print("\nTabuleiro atualizado pelo servidor:")
            exibir_tabuleiro(resposta["board"])

            return resposta["board"]

        print("Status desconhecido:", resultado["status"])
        return tabuleiro_atual

    except (TransportError, ProtocolError) as erro:
        print("Erro ao processar resultado:", erro)
        return tabuleiro_atual



def processar_fim_partida(conexao, mensagem=None):
    """Recebe e apresenta o encerramento da partida."""

    try:
        # Se a mensagem ainda não foi recebida, busca na conexão.
        if mensagem is None:
            mensagem = conexao.receive_message()

        if mensagem["type"] != "GAME_OVER":
            print("Resposta inesperada:", mensagem["type"])
            return None

        resultado = mensagem["result"]

        print("\n=== FIM DE PARTIDA ===")

        if resultado == "WIN":
            vencedor = mensagem["winner"]
            print("Partida encerrada!")
            print("Vencedor:", vencedor)

        elif resultado == "DRAW":
            print("A partida terminou em empate!")

        elif resultado == "ABORTED":
            print("A partida foi interrompida.")
            print("Motivo:", mensagem["reason"])

        return mensagem

    except (TransportError, ProtocolError) as erro:
        print("Erro ao receber encerramento:", erro)
        return None


def _vencedor_tabuleiro(tabuleiro):
    linhas = tabuleiro + [list(coluna) for coluna in zip(*tabuleiro)]
    linhas.extend(
        (
            [tabuleiro[0][0], tabuleiro[1][1], tabuleiro[2][2]],
            [tabuleiro[0][2], tabuleiro[1][1], tabuleiro[2][0]],
        )
    )
    for linha in linhas:
        if linha[0] and linha[0] == linha[1] == linha[2]:
            return linha[0]
    return None


def _validar_board_atualizado(
    estado,
    game_id,
    board_anterior,
    revisao_anterior,
    marca_jogada,
    posicao_esperada=None,
):
    """Confere identidade, revisão e efeito de uma única jogada aceita."""

    if estado.get("type") != "BOARD":
        print("Esperava BOARD, mas recebeu:", estado.get("type"))
        return False
    if estado["game_id"] != game_id:
        print("BOARD recebido pertence a outra partida.")
        return False
    if estado["revision"] != revisao_anterior + 1:
        print("BOARD recebido tem revisão inesperada.")
        return False

    alteracoes = []
    for linha in range(3):
        for coluna in range(3):
            anterior = board_anterior[linha][coluna]
            atual = estado["board"][linha][coluna]
            if anterior != atual:
                alteracoes.append((linha, coluna, anterior, atual))

    if (
        len(alteracoes) != 1
        or alteracoes[0][2] != ""
        or alteracoes[0][3] != marca_jogada
        or (
            posicao_esperada is not None
            and alteracoes[0][:2] != posicao_esperada
        )
    ):
        print("BOARD não representa exatamente a jogada aceita.")
        return False

    ganhador = _vencedor_tabuleiro(estado["board"])
    tabuleiro_cheio = all(
        celula for linha in estado["board"] for celula in linha
    )
    terminou = ganhador is not None or tabuleiro_cheio
    turno_esperado = None if terminou else ("O" if marca_jogada == "X" else "X")

    if estado["turn"] != turno_esperado:
        print("Turno do BOARD é incompatível com o tabuleiro recebido.")
        return False
    return True


def _validar_fim_partida(mensagem, game_id, tabuleiro=None):
    """Confere se GAME_OVER identifica a partida e combina com o tabuleiro."""

    if mensagem.get("type") != "GAME_OVER":
        print("Esperava GAME_OVER, mas recebeu:", mensagem.get("type"))
        return False
    if mensagem["game_id"] != game_id:
        print("GAME_OVER recebido pertence a outra partida.")
        return False

    if tabuleiro is None:
        if mensagem["result"] != "ABORTED":
            print("GAME_OVER chegou sem um tabuleiro terminal correspondente.")
            return False
        return True

    ganhador = _vencedor_tabuleiro(tabuleiro)
    tabuleiro_cheio = all(celula for linha in tabuleiro for celula in linha)

    if mensagem["result"] == "WIN":
        if ganhador is None or mensagem["winner"] != ganhador:
            print("Vencedor de GAME_OVER não corresponde ao tabuleiro.")
            return False
    elif mensagem["result"] == "DRAW":
        if ganhador is not None or not tabuleiro_cheio:
            print("Empate de GAME_OVER não corresponde ao tabuleiro.")
            return False
    elif mensagem["result"] == "ABORTED":
        print("GAME_OVER(ABORTED) não combina com um BOARD terminal.")
        return False
    else:
        print("Resultado GAME_OVER inválido.")
        return False
    return True




def executar_partida(conexao, resposta_start):
    """Controla o fluxo completo de uma partida."""

    estado = iniciar_partida(conexao, resposta_start)

    if estado is None:
        return False

    game_id = resposta_start["game_id"]
    minha_marca = resposta_start["mark"]

    tabuleiro = estado["board"]
    revisao = estado["revision"]
    turno = estado["turn"]

    while True:

        # Verifica se a partida já terminou.
        if turno is None:
            try:
                fim = conexao.receive_message()
            except (TransportError, ProtocolError) as erro:
                print("Erro ao receber GAME_OVER:", erro)
                return False
            if not _validar_fim_partida(fim, game_id, tabuleiro):
                return False
            return processar_fim_partida(conexao, fim)

        # Quando for a vez deste jogador.
        if turno == minha_marca:

            print("\nSua vez de jogar!")

            linha, coluna = solicitar_jogada()

            if not enviar_jogada(
                conexao,
                game_id,
                linha,
                coluna
            ):
                return False

            try:
                resposta = conexao.receive_message()

            except (TransportError, ProtocolError) as erro:
                print("Erro ao receber resposta da jogada:", erro)
                return False

            if resposta["type"] == "ERROR":
                print("Erro do servidor:", resposta["message"])
                return False

            if resposta["type"] != "MOVE_RESULT":
                print("Resposta inesperada:", resposta["type"])
                return False

            if resposta["game_id"] != game_id:
                print("MOVE_RESULT recebido pertence a outra partida.")
                return False

            if resposta["status"] == "REJECTED":
                print("\nJogada recusada pelo servidor.")
                print("Motivo:", resposta["message"])
                continue

            if resposta["status"] != "ACCEPTED":
                print("Status desconhecido:", resposta["status"])
                return False

            if (
                resposta["row"] != linha
                or resposta["col"] != coluna
                or resposta["revision"] != revisao + 1
            ):
                print("MOVE_RESULT não corresponde à jogada enviada.")
                return False

            print("\nJogada aceita pelo servidor!")

            # Recebe o tabuleiro oficial atualizado.
            try:
                estado = conexao.receive_message()

            except (TransportError, ProtocolError) as erro:
                print("Erro ao receber tabuleiro:", erro)
                return False

        else:
            # Quando for a vez do adversário.
            print("\nAguardando jogada do adversário...")

            try:
                estado = conexao.receive_message()

            except (TransportError, ProtocolError) as erro:
                print("Erro ao aguardar adversário:", erro)
                return False

        if estado["type"] == "ERROR":
            print("Erro do servidor:", estado["message"])
            return False

        # Verifica se o servidor encerrou a partida.
        if estado["type"] == "GAME_OVER":
            if not _validar_fim_partida(estado, game_id):
                return False
            return processar_fim_partida(conexao, estado)

        marca_jogada = minha_marca if turno == minha_marca else turno
        if not _validar_board_atualizado(
            estado,
            game_id,
            tabuleiro,
            revisao,
            marca_jogada,
            (linha, coluna) if marca_jogada == minha_marca else None,
        ):
            return False

        # Atualiza somente com o tabuleiro oficial.
        tabuleiro = estado["board"]
        revisao = estado["revision"]
        turno = estado["turn"]

        print("\nTabuleiro atualizado:")
        exibir_tabuleiro(tabuleiro)

        # O servidor informa turno None quando a partida termina.
        if turno is None:
            try:
                fim = conexao.receive_message()
            except (TransportError, ProtocolError) as erro:
                print("Erro ao receber GAME_OVER:", erro)
                return False
            if not _validar_fim_partida(fim, game_id, tabuleiro):
                return False
            return processar_fim_partida(conexao, fim)


def criar_placar():
    return {"VOCE": 0, "ADVERSARIO": 0, "DRAW": 0}


def registrar_resultado(placar, fim, minha_marca):
    """Atualiza o placar somente com resultado oficial WIN ou DRAW."""

    if fim["result"] == "WIN":
        chave = "VOCE" if fim["winner"] == minha_marca else "ADVERSARIO"
        placar[chave] += 1
    elif fim["result"] == "DRAW":
        placar["DRAW"] += 1


def exibir_placar(placar, titulo="Placar"):
    print(
        f"\n{titulo}: Você {placar['VOCE']} | "
        f"Adversário {placar['ADVERSARIO']} | "
        f"Empates {placar['DRAW']}"
    )


def pedir_revanche(conexao):
    """Solicita outra partida na mesma conexão TCP."""

    while True:
        resposta = input("\nJogar novamente? (s/n): ").strip().lower()
        if resposta in {"s", "sim"}:
            conexao.send_message(make_message("JOIN"))
            return True
        if resposta in {"n", "nao", "não"}:
            conexao.send_message(make_message("QUIT"))
            return False
        print("Digite s para sim ou n para não.")


def aguardar_revanche(conexao, game_id_anterior):
    """Aguarda o servidor iniciar a revanche ou informar que ela foi cancelada."""

    try:
        resposta = conexao.receive_message()
    except (TransportError, ProtocolError) as erro:
        print(
            "A revanche não começou; o adversário recusou ou a conexão foi encerrada.",
            erro,
        )
        return None

    if resposta["type"] == "START":
        if resposta["game_id"] == game_id_anterior:
            print("O servidor reutilizou o game_id da partida anterior.")
            return None
        print("\nRevanche iniciada!")
        return resposta

    if resposta["type"] == "GAME_OVER":
        print("Resposta inesperada: GAME_OVER durante a negociação da revanche.")
        return None

    if resposta["type"] == "ERROR":
        print("Erro do servidor:", resposta["message"])
    else:
        print("Resposta inesperada:", resposta["type"])
    return None

def main():
    """Executa o menu principal do cliente."""

    parser = argparse.ArgumentParser(
        description="Cliente do Jogo da Velha"
    )

    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Endereço IP do servidor"
    )

    parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="Porta do servidor"
    )

    args = parser.parse_args()

    while True:
        print("\n================================")
        print("          JOGO DA VELHA")
        print("================================")
        print("\n1 - Conectar e jogar")
        print("2 - Sair")

        opcao = input("\nEscolha uma opção: ").strip()

        if opcao == "1":
            conexao = conectar_servidor(args.host, args.port)

            if conexao is None:
                continue

            try:
                resposta_start = entrar_no_lobby(conexao)
                placar = criar_placar()
                partidas_concluidas = 0

                while resposta_start is not None:
                    fim = executar_partida(conexao, resposta_start)
                    if not isinstance(fim, dict):
                        break

                    if fim["result"] in {"WIN", "DRAW"}:
                        registrar_resultado(
                            placar,
                            fim,
                            resposta_start["mark"],
                        )
                        partidas_concluidas += 1
                        exibir_placar(placar)
                    else:
                        break

                    if not pedir_revanche(conexao):
                        break
                    resposta_start = aguardar_revanche(
                        conexao,
                        resposta_start["game_id"],
                    )

                if partidas_concluidas:
                    exibir_placar(placar, "Placar final da sessão")

            finally:
                close_connection(conexao)
                print("\nConexão encerrada.")

        elif opcao == "2":
            print("\nObrigado por jogar!")
            break

        else:
            print("\nOpção inválida! Escolha 1 ou 2.")


if __name__ == "__main__":
    main()

