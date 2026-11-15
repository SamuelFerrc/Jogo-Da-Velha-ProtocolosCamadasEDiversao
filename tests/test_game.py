import threading
import unittest

from server.game import Game, GameStatus, empty_board, find_winner, is_full


def new_game() -> Game:
    return Game("g1", "px", "po")


def play_sequence(game: Game, moves: list[tuple[str, int, int]]):
    outcome = None
    for player, row, col in moves:
        outcome = game.play(player, "g1", row, col)
        assert outcome.accepted, outcome
    return outcome


class RulesTests(unittest.TestCase):
    def test_x_wins_row(self) -> None:
        game = new_game()
        outcome = play_sequence(
            game,
            [("px", 0, 0), ("po", 1, 0), ("px", 0, 1), ("po", 1, 1), ("px", 0, 2)],
        )
        self.assertEqual((outcome.result, outcome.winner), ("WIN", "X"))
        self.assertIsNone(outcome.snapshot.turn)
        self.assertEqual(outcome.snapshot.revision, 5)
        self.assertIs(game.status, GameStatus.FINISHED)

    def test_o_wins_row(self) -> None:
        game = new_game()
        outcome = play_sequence(
            game,
            [
                ("px", 0, 0), ("po", 1, 0), ("px", 0, 1),
                ("po", 1, 1), ("px", 2, 2), ("po", 1, 2),
            ],
        )
        self.assertEqual((outcome.result, outcome.winner), ("WIN", "O"))

    def test_draw(self) -> None:
        game = new_game()
        outcome = play_sequence(
            game,
            [
                ("px", 0, 0), ("po", 0, 1), ("px", 0, 2),
                ("po", 1, 1), ("px", 1, 0), ("po", 1, 2),
                ("px", 2, 1), ("po", 2, 0), ("px", 2, 2),
            ],
        )
        self.assertEqual((outcome.result, outcome.winner), ("DRAW", None))
        self.assertIsNone(outcome.snapshot.turn)
        self.assertEqual(outcome.snapshot.revision, 9)

    def test_all_eight_lines_detected(self) -> None:
        lines = [
            [(0, 0), (0, 1), (0, 2)], [(1, 0), (1, 1), (1, 2)], [(2, 0), (2, 1), (2, 2)],
            [(0, 0), (1, 0), (2, 0)], [(0, 1), (1, 1), (2, 1)], [(0, 2), (1, 2), (2, 2)],
            [(0, 0), (1, 1), (2, 2)], [(0, 2), (1, 1), (2, 0)],
        ]
        for line in lines:
            rows = [["", "", ""] for _ in range(3)]
            for r, c in line:
                rows[r][c] = "O"
            board = tuple(tuple(r) for r in rows)
            self.assertEqual(find_winner(board), "O", line)
        self.assertIsNone(find_winner(empty_board()))
        self.assertFalse(is_full(empty_board()))

    def test_turn_alternates_and_revision_increments(self) -> None:
        game = new_game()
        self.assertEqual(game.snapshot().turn, "X")
        out = game.play("px", "g1", 1, 1)
        self.assertEqual((out.snapshot.turn, out.snapshot.revision), ("O", 1))
        self.assertEqual(out.snapshot.board[1][1], "X")


class RejectionTests(unittest.TestCase):
    def assert_rejected(self, game: Game, code: str, *args) -> None:
        before = game.snapshot()
        outcome = game.play(*args)
        self.assertFalse(outcome.accepted)
        self.assertEqual(outcome.code, code)
        self.assertEqual(game.snapshot(), before)

    def test_not_your_turn(self) -> None:
        game = new_game()
        self.assert_rejected(game, "NOT_YOUR_TURN", "po", "g1", 0, 0)
        game.play("px", "g1", 0, 0)
        self.assert_rejected(game, "NOT_YOUR_TURN", "px", "g1", 1, 1)

    def test_occupied(self) -> None:
        game = new_game()
        game.play("px", "g1", 0, 0)
        self.assert_rejected(game, "OCCUPIED", "po", "g1", 0, 0)

    def test_invalid_position(self) -> None:
        game = new_game()
        for row, col in [(-1, 0), (3, 0), (0, -1), (0, 3), (True, 0), (0, False),
                         (1.0, 0), ("1", 1), ([1], 1), (None, 0)]:
            self.assert_rejected(game, "INVALID_POSITION", "px", "g1", row, col)

    def test_not_in_game(self) -> None:
        game = new_game()
        self.assert_rejected(game, "NOT_IN_GAME", "intruso", "g1", 0, 0)
        self.assert_rejected(game, "NOT_IN_GAME", "px", "g99", 0, 0)

    def test_move_after_game_over(self) -> None:
        game = new_game()
        play_sequence(
            game,
            [("px", 0, 0), ("po", 1, 0), ("px", 0, 1), ("po", 1, 1), ("px", 0, 2)],
        )
        self.assert_rejected(game, "GAME_FINISHED", "po", "g1", 2, 2)

    def test_move_after_abort(self) -> None:
        game = new_game()
        self.assertTrue(game.abort())
        self.assertFalse(game.abort())
        self.assertIs(game.status, GameStatus.ABORTED)
        self.assertIsNone(game.snapshot().turn)
        self.assert_rejected(game, "GAME_FINISHED", "px", "g1", 0, 0)

    def test_requires_distinct_players(self) -> None:
        with self.assertRaises(ValueError):
            Game("g", "a", "a")


class ConcurrencyTests(unittest.TestCase):
    def test_concurrent_moves_apply_once_per_turn(self) -> None:
        for _ in range(50):
            game = new_game()
            barrier = threading.Barrier(2)
            outcomes = []

            def attempt(player: str, row: int, col: int) -> None:
                barrier.wait()
                outcomes.append(game.play(player, "g1", row, col))

            threads = [
                threading.Thread(target=attempt, args=("px", 0, 0)),
                threading.Thread(target=attempt, args=("px", 1, 1)),
            ]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            self.assertEqual(sum(o.accepted for o in outcomes), 1)
            self.assertEqual(game.snapshot().revision, 1)


if __name__ == "__main__":
    unittest.main()
