
import unittest
from unittest.mock import Mock, patch

from client.client import (
    conectar_servidor,
    entrar_no_lobby,
    iniciar_partida,
    enviar_jogada,
    processar_fim_partida,
    processar_resultado_jogada,
    aguardar_inicio_partida,
    executar_partida,
    _validar_board_atualizado,
    _validar_fim_partida,
    criar_placar,
    registrar_resultado,
    exibir_placar,
    pedir_revanche,
    aguardar_revanche,
)


class TestCliente(unittest.TestCase):

    def test_entrar_no_lobby_com_sucesso(self):
        conexao = Mock()

        conexao.receive_message.side_effect = [
            {"type": "WELCOME"},
            {"type": "WAITING"},
            {
                "type": "START",
                "game_id": "partida-001",
                "mark": "X",
                "first_turn": "X"
            }
        ]

        resultado = entrar_no_lobby(conexao)

        self.assertEqual(resultado["type"], "START")
        self.assertEqual(resultado["game_id"], "partida-001")

        chamadas = conexao.send_message.call_args_list

        self.assertEqual(chamadas[0].args[0]["type"], "HELLO")
        self.assertEqual(chamadas[1].args[0]["type"], "JOIN")

    def test_iniciar_partida_com_sucesso(self):
        conexao = Mock()

        tabuleiro = [
            ["", "", ""],
            ["", "", ""],
            ["", "", ""]
        ]

        conexao.receive_message.return_value = {
            "type": "BOARD",
            "game_id": "partida-001",
            "board": tabuleiro,
            "turn": "X",
            "revision": 0
        }

        resposta_start = {
            "type": "START",
            "game_id": "partida-001",
            "mark": "X",
            "first_turn": "X"
        }

        resultado = iniciar_partida(conexao, resposta_start)

        self.assertEqual(resultado["type"], "BOARD")
        self.assertEqual(resultado["board"], tabuleiro)
        self.assertEqual(resultado["turn"], "X")
    def test_enviar_jogada_com_sucesso(self):
        conexao = Mock()

        resultado = enviar_jogada(
            conexao,
            "partida-001",
            1,
            2
        )

        self.assertTrue(resultado)

        mensagem = conexao.send_message.call_args.args[0]

        self.assertEqual(mensagem["type"], "MOVE")
        self.assertEqual(mensagem["game_id"], "partida-001")
        self.assertEqual(mensagem["row"], 1)
        self.assertEqual(mensagem["col"], 2)
    def test_enviar_jogada_com_coordenadas_invalidas(self):
        conexao = Mock()

        resultado = enviar_jogada(
            conexao,
            "partida-001",
            3,
            1
        )

        self.assertFalse(resultado)
        conexao.send_message.assert_not_called()
    def test_processar_fim_partida_empate(self):
        conexao = Mock()

        conexao.receive_message.return_value = {
            "type": "GAME_OVER",
            "game_id": "partida-001",
            "result": "DRAW",
            "winner": None
        }

        resultado = processar_fim_partida(conexao)

        self.assertIsNotNone(resultado)
        self.assertEqual(resultado["result"], "DRAW")
        conexao.receive_message.assert_called_once()
    def test_processar_fim_partida_vitoria(self):
        conexao = Mock()

        conexao.receive_message.return_value = {
            "type": "GAME_OVER",
            "game_id": "partida-001",
            "result": "WIN",
            "winner": "X"
        }

        resultado = processar_fim_partida(conexao)

        self.assertIsNotNone(resultado)
        self.assertEqual(resultado["result"], "WIN")
        self.assertEqual(resultado["winner"], "X")
        conexao.receive_message.assert_called_once()
    def test_processar_fim_partida_abandono(self):
        conexao = Mock()

        conexao.receive_message.return_value = {
            "type": "GAME_OVER",
            "game_id": "partida-001",
            "result": "ABORTED",
            "winner": None,
            "reason": "OPPONENT_LEFT"
        }

        resultado = processar_fim_partida(conexao)

        self.assertIsNotNone(resultado)
        self.assertEqual(resultado["result"], "ABORTED")
        self.assertEqual(resultado["reason"], "OPPONENT_LEFT")
        conexao.receive_message.assert_called_once()
    def test_jogada_recusada_nao_altera_tabuleiro(self):
        conexao = Mock()

        tabuleiro = [
            ["X", "", ""],
            ["", "O", ""],
            ["", "", ""]
        ]

        conexao.receive_message.return_value = {
            "type": "MOVE_RESULT",
            "game_id": "partida-001",
            "status": "REJECTED",
            "code": "OCCUPIED",
            "message": "A posição já está ocupada."
        }

        resultado = processar_resultado_jogada(
            conexao,
            tabuleiro
        )

        self.assertEqual(resultado, tabuleiro)
        self.assertEqual(resultado[0][0], "X")
        self.assertEqual(resultado[1][1], "O")
        conexao.receive_message.assert_called_once()
    def test_jogada_aceita_atualiza_tabuleiro(self):
        conexao = Mock()

        tabuleiro_atualizado = [
            ["X", "", ""],
            ["", "O", ""],
            ["", "", ""]
        ]

        conexao.receive_message.side_effect = [
            {
                "type": "MOVE_RESULT",
                "game_id": "partida-001",
                "status": "ACCEPTED",
                "row": 0,
                "col": 0,
                "revision": 1
            },
            {
                "type": "BOARD",
                "game_id": "partida-001",
                "board": tabuleiro_atualizado,
                "turn": "O",
                "revision": 1
            }
        ]

        resultado = processar_resultado_jogada(
            conexao,
            [["", "", ""], ["", "", ""], ["", "", ""]]
        )

        self.assertEqual(resultado, tabuleiro_atualizado)
        self.assertEqual(resultado[0][0], "X")
        self.assertEqual(resultado[1][1], "O")
        self.assertEqual(conexao.receive_message.call_count, 2)
    def test_entrar_no_lobby_com_partida_iniciada(self):
        conexao = Mock()

        conexao.receive_message.side_effect = [
            {"type": "WELCOME"},
            {
                "type": "START",
                "game_id": "partida-001",
                "mark": "X",
                "first_turn": "X"
            }
        ]

        resultado = entrar_no_lobby(conexao)

        self.assertEqual(resultado["type"], "START")
        self.assertEqual(resultado["game_id"], "partida-001")
        self.assertEqual(resultado["mark"], "X")
    def test_entrar_no_lobby_com_erro(self):
        conexao = Mock()

        conexao.receive_message.side_effect = [
            {"type": "WELCOME"},
            {
                "type": "ERROR",
                "code": "INVALID_STATE",
                "message": "Não foi possível entrar no lobby."
            }
        ]

        resultado = entrar_no_lobby(conexao)

        self.assertIsNone(resultado)
        self.assertEqual(conexao.send_message.call_count, 2)
    @patch("client.client.connect_to_server")
    def test_conectar_servidor_com_sucesso(self, mock_conectar):
        conexao_falsa = Mock()
        mock_conectar.return_value = conexao_falsa

        resultado = conectar_servidor("127.0.0.1", 5000)

        self.assertIs(resultado, conexao_falsa)
        mock_conectar.assert_called_once_with("127.0.0.1", 5000)
    @patch("client.client.connect_to_server")
    def test_conectar_servidor_com_falha(self, mock_conectar):
        from client.client import TransportError

        mock_conectar.side_effect = TransportError(
            "Conexão recusada."
        )

        resultado = conectar_servidor("127.0.0.1", 5000)

        self.assertIsNone(resultado)
        mock_conectar.assert_called_once_with("127.0.0.1", 5000)
    def test_processar_fim_partida_com_mensagem_recebida(self):
        conexao = Mock()

        mensagem = {
            "type": "GAME_OVER",
            "game_id": "partida-001",
            "result": "ABORTED",
            "winner": None,
            "reason": "OPPONENT_LEFT"
        }

        resultado = processar_fim_partida(conexao, mensagem)

        self.assertEqual(resultado, mensagem)
        conexao.receive_message.assert_not_called()
    def test_iniciar_partida_com_resposta_inesperada(self):
        conexao = Mock()

        conexao.receive_message.return_value = {
            "type": "ERROR",
            "code": "INVALID_STATE",
            "message": "Estado inválido."
        }

        resposta_start = {
            "type": "START",
            "game_id": "partida-001",
            "mark": "X",
            "first_turn": "X"
        }

        resultado = iniciar_partida(conexao, resposta_start)

        self.assertIsNone(resultado)
        conexao.receive_message.assert_called_once()
    def test_entrar_no_lobby_com_resposta_inesperada(self):
        conexao = Mock()

        conexao.receive_message.side_effect = [
            {"type": "WELCOME"},
            {"type": "BOARD"}
        ]

        resultado = entrar_no_lobby(conexao)

        self.assertIsNone(resultado)
        self.assertEqual(conexao.send_message.call_count, 2)

    def test_aguardar_inicio_partida_apos_waiting(self):
        conexao = Mock()

        conexao.receive_message.return_value = {
            "type": "START",
            "game_id": "partida-001",
            "mark": "O",
            "first_turn": "X"
        }

        resposta_lobby = {
            "type": "WAITING"
        }

        resultado = aguardar_inicio_partida(
            conexao,
            resposta_lobby
        )

        self.assertEqual(resultado["type"], "START")
        self.assertEqual(resultado["game_id"], "partida-001")
        self.assertEqual(resultado["mark"], "O")
        conexao.receive_message.assert_called_once()

    def test_aguardar_inicio_partida_com_start_direto(self):
        conexao = Mock()

        resposta = {
            "type": "START",
            "game_id": "partida-002",
            "mark": "O",
            "first_turn": "X"
        }

        resultado = aguardar_inicio_partida(conexao, resposta)

        self.assertEqual(resultado, resposta)
        conexao.receive_message.assert_not_called()

    def test_aguardar_inicio_partida_com_erro(self):
        conexao = Mock()

        conexao.receive_message.return_value = {
            "type": "ERROR",
            "code": "INVALID_STATE",
            "message": "Não foi possível iniciar."
        }

        resultado = aguardar_inicio_partida(
            conexao,
            {"type": "WAITING"}
        )

        self.assertIsNone(resultado)
        conexao.receive_message.assert_called_once()

    def test_aguardar_inicio_partida_com_resposta_inesperada(self):
        conexao = Mock()

        conexao.receive_message.return_value = {
            "type": "BOARD"
        }

        resultado = aguardar_inicio_partida(
            conexao,
            {"type": "WAITING"}
        )

        self.assertIsNone(resultado)
        conexao.receive_message.assert_called_once()

    def test_enviar_jogada_com_coluna_invalida(self):
        conexao = Mock()

        resultado = enviar_jogada(
            conexao,
            "partida-001",
            1,
            3
        )

        self.assertFalse(resultado)
        conexao.send_message.assert_not_called()

    def test_enviar_jogada_com_coordenada_booleana(self):
        conexao = Mock()

        resultado = enviar_jogada(
            conexao,
            "partida-001",
            True,
            1
        )

        self.assertFalse(resultado)
        conexao.send_message.assert_not_called()

    def test_processar_resultado_com_resposta_inesperada(self):
        conexao = Mock()

        tabuleiro = [
            ["X", "", ""],
            ["", "O", ""],
            ["", "", ""]
        ]

        conexao.receive_message.return_value = {
            "type": "ERROR",
            "message": "Erro inesperado."
        }

        resultado = processar_resultado_jogada(
            conexao,
            tabuleiro
        )

        self.assertEqual(resultado, tabuleiro)
        conexao.receive_message.assert_called_once()

    def test_enviar_jogada_com_falha_de_comunicacao(self):
        from client.client import TransportError

        conexao = Mock()
        conexao.send_message.side_effect = TransportError(
            "Conexão perdida."
        )

        resultado = enviar_jogada(
            conexao,
            "partida-001",
            1,
            1
        )

        self.assertFalse(resultado)
        conexao.send_message.assert_called_once()

    def test_processar_resultado_com_desconexao(self):
        from client.client import TransportError

        conexao = Mock()
        tabuleiro = [
            ["X", "", ""],
            ["", "O", ""],
            ["", "", ""]
        ]

        conexao.receive_message.side_effect = TransportError(
            "Conexão perdida."
        )

        resultado = processar_resultado_jogada(
            conexao,
            tabuleiro
        )

        self.assertEqual(resultado, tabuleiro)
        conexao.receive_message.assert_called_once()

    def test_aguardar_inicio_partida_com_desconexao(self):
        from client.client import TransportError

        conexao = Mock()
        conexao.receive_message.side_effect = TransportError(
            "Conexão perdida."
        )

        resultado = aguardar_inicio_partida(
            conexao,
            {"type": "WAITING"}
        )

        self.assertIsNone(resultado)
        conexao.receive_message.assert_called_once()

    def test_executar_partida_com_jogada_aceita(self):
        conexao = Mock()
        estado_inicial = {
            "board": [["X", "X", ""], ["O", "O", ""], ["", "", ""]],
            "turn": "X",
            "revision": 4,
        }
        estado_final = {
            "type": "BOARD",
            "game_id": "partida-001",
            "board": [["X", "X", "X"], ["O", "O", ""], ["", "", ""]],
            "turn": None,
            "revision": 5,
        }
        conexao.receive_message.side_effect = [
            {
                "type": "MOVE_RESULT",
                "game_id": "partida-001",
                "status": "ACCEPTED",
                "row": 0,
                "col": 2,
                "revision": 5,
            },
            estado_final,
            {
                "type": "GAME_OVER",
                "game_id": "partida-001",
                "result": "WIN",
                "winner": "X",
            },
        ]

        with patch("client.client.iniciar_partida", return_value=estado_inicial), \
             patch("client.client.solicitar_jogada", return_value=(0, 2)), \
             patch("client.client.enviar_jogada", return_value=True), \
             patch("client.client.processar_fim_partida", return_value={"result": "WIN"}):

            resultado = executar_partida(
                conexao,
                {
                    "game_id": "partida-001",
                    "mark": "X"
                }
            )

        self.assertEqual(resultado, {"result": "WIN"})

    def test_executar_partida_com_jogada_recusada_e_depois_aceita(self):
        conexao = Mock()
        estado_inicial = {
            "board": [["X", "X", ""], ["O", "O", ""], ["", "", ""]],
            "turn": "X",
            "revision": 4,
        }
        estado_final = {
            "type": "BOARD",
            "game_id": "partida-001",
            "board": [["X", "X", "X"], ["O", "O", ""], ["", "", ""]],
            "turn": None,
            "revision": 5,
        }
        conexao.receive_message.side_effect = [
            {
                "type": "MOVE_RESULT",
                "game_id": "partida-001",
                "status": "REJECTED",
                "code": "OCCUPIED",
                "message": "Posição ocupada."
            },
            {
                "type": "MOVE_RESULT",
                "game_id": "partida-001",
                "status": "ACCEPTED",
                "row": 0,
                "col": 2,
                "revision": 5,
            },
            estado_final,
            {
                "type": "GAME_OVER",
                "game_id": "partida-001",
                "result": "WIN",
                "winner": "X",
            },
        ]

        with patch("client.client.iniciar_partida", return_value=estado_inicial), \
             patch(
                 "client.client.solicitar_jogada",
                 side_effect=[(0, 1), (0, 2)],
             ) as solicitar, \
             patch("client.client.enviar_jogada", return_value=True), \
             patch("client.client.processar_fim_partida", return_value={"result": "WIN"}):

            resultado = executar_partida(
                conexao,
                {
                    "game_id": "partida-001",
                    "mark": "X"
                }
            )

        self.assertEqual(resultado, {"result": "WIN"})
        self.assertEqual(solicitar.call_count, 2)

    def test_executar_partida_aguardando_adversario(self):
        conexao = Mock()
        estado_inicial = {
            "board": [["O", "O", ""], ["X", "X", ""], ["X", "", ""]],
            "turn": "O",
            "revision": 5,
        }
        estado_final = {
            "type": "BOARD",
            "game_id": "partida-001",
            "board": [["O", "O", "O"], ["X", "X", ""], ["X", "", ""]],
            "turn": None,
            "revision": 6,
        }
        conexao.receive_message.side_effect = [
            estado_final,
            {
                "type": "GAME_OVER",
                "game_id": "partida-001",
                "result": "WIN",
                "winner": "O",
            },
        ]

        with patch("client.client.iniciar_partida", return_value=estado_inicial), \
             patch("client.client.solicitar_jogada") as solicitar, \
             patch("client.client.processar_fim_partida", return_value={"result": "WIN"}):

            resultado = executar_partida(
                conexao,
                {
                    "game_id": "partida-001",
                    "mark": "X"
                }
            )

        self.assertEqual(resultado, {"result": "WIN"})
        solicitar.assert_not_called()
        self.assertEqual(conexao.receive_message.call_count, 2)

    def test_board_confere_game_id_revisao_e_jogada(self):
        tabuleiro_anterior = [["", "", ""], ["", "", ""], ["", "", ""]]
        snapshot = {
            "type": "BOARD",
            "game_id": "partida-001",
            "board": [["X", "", ""], ["", "", ""], ["", "", ""]],
            "turn": "O",
            "revision": 1,
        }

        self.assertTrue(
            _validar_board_atualizado(
                snapshot, "partida-001", tabuleiro_anterior, 0, "X", (0, 0)
            )
        )
        self.assertFalse(
            _validar_board_atualizado(
                snapshot, "outra-partida", tabuleiro_anterior, 0, "X", (0, 0)
            )
        )
        self.assertFalse(
            _validar_board_atualizado(
                snapshot, "partida-001", tabuleiro_anterior, 1, "X", (0, 0)
            )
        )
        self.assertFalse(
            _validar_board_atualizado(
                snapshot, "partida-001", tabuleiro_anterior, 0, "X", (1, 1)
            )
        )

    def test_game_over_confere_vencedor_empate_e_game_id(self):
        vitoria_tabuleiro = [
            ["X", "X", "X"], ["O", "O", ""], ["", "", ""]
        ]
        vitoria = {
            "type": "GAME_OVER",
            "game_id": "partida-001",
            "result": "WIN",
            "winner": "X",
        }
        self.assertTrue(
            _validar_fim_partida(vitoria, "partida-001", vitoria_tabuleiro)
        )
        self.assertFalse(
            _validar_fim_partida(vitoria, "partida-002", vitoria_tabuleiro)
        )

        empate_tabuleiro = [
            ["X", "O", "X"], ["X", "O", "O"], ["O", "X", "X"]
        ]
        empate = {
            "type": "GAME_OVER",
            "game_id": "partida-001",
            "result": "DRAW",
            "winner": None,
        }
        self.assertTrue(_validar_fim_partida(empate, "partida-001", empate_tabuleiro))
        self.assertFalse(_validar_fim_partida(empate, "partida-001", vitoria_tabuleiro))

    def test_move_result_rejeita_coordenada_diferente_da_enviada(self):
        conexao = Mock()
        estado_inicial = {
            "board": [["", "", ""], ["", "", ""], ["", "", ""]],
            "turn": "X",
            "revision": 0,
        }
        conexao.receive_message.return_value = {
            "type": "MOVE_RESULT",
            "game_id": "partida-001",
            "status": "ACCEPTED",
            "row": 1,
            "col": 1,
            "revision": 1,
        }

        with patch("client.client.iniciar_partida", return_value=estado_inicial), \
             patch("client.client.solicitar_jogada", return_value=(0, 0)), \
             patch("client.client.enviar_jogada", return_value=True):
            resultado = executar_partida(
                conexao,
                {"game_id": "partida-001", "mark": "X"},
            )

        self.assertFalse(resultado)
        conexao.receive_message.assert_called_once()

    def test_placar_acompanha_jogadores_quando_as_marcas_trocam(self):
        placar = criar_placar()
        registrar_resultado(placar, {"result": "WIN", "winner": "X"}, "X")
        registrar_resultado(placar, {"result": "WIN", "winner": "O"}, "X")
        registrar_resultado(placar, {"result": "DRAW", "winner": None}, "O")

        self.assertEqual(
            placar,
            {"VOCE": 1, "ADVERSARIO": 1, "DRAW": 1},
        )
        with patch("builtins.print") as imprimir:
            exibir_placar(placar, "Placar final")
        self.assertIn("Você 1", imprimir.call_args.args[0])
        self.assertIn("Empates 1", imprimir.call_args.args[0])

    @patch("builtins.input", return_value="s")
    def test_aceitar_revanche_envia_join(self, _entrada):
        conexao = Mock()
        self.assertTrue(pedir_revanche(conexao))
        self.assertEqual(conexao.send_message.call_args.args[0]["type"], "JOIN")

    @patch("builtins.input", return_value="n")
    def test_recusar_revanche_envia_quit(self, _entrada):
        conexao = Mock()
        self.assertFalse(pedir_revanche(conexao))
        self.assertEqual(conexao.send_message.call_args.args[0]["type"], "QUIT")

    def test_revanche_exige_novo_game_id(self):
        conexao = Mock()
        conexao.receive_message.return_value = {
            "type": "START",
            "game_id": "partida-002",
            "mark": "O",
            "first_turn": "X",
        }

        resultado = aguardar_revanche(conexao, "partida-001")
        self.assertEqual(resultado["game_id"], "partida-002")

        conexao.receive_message.return_value["game_id"] = "partida-001"
        self.assertIsNone(aguardar_revanche(conexao, "partida-001"))




if __name__ == "__main__":
    unittest.main()
