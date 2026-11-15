import threading
import unittest

from server.lobby import Lobby


class FakeParticipant:
    def __init__(self, client_id: str, connected: bool = True) -> None:
        self.client_id = client_id
        self.connected = connected

    def is_connected(self) -> bool:
        return self.connected


class LobbyTests(unittest.TestCase):
    def test_first_waits_second_forms_game(self) -> None:
        lobby = Lobby()
        a, b = FakeParticipant("c1"), FakeParticipant("c2")
        self.assertIsNone(lobby.join(a))
        self.assertEqual(lobby.waiting_count(), 1)
        game = lobby.join(b)
        self.assertEqual(game.players, {"X": "c1", "O": "c2"})
        self.assertEqual(lobby.waiting_count(), 0)

    def test_game_ids_are_unique(self) -> None:
        lobby = Lobby()
        ids = set()
        for i in range(5):
            lobby.join(FakeParticipant(f"a{i}"))
            ids.add(lobby.join(FakeParticipant(f"b{i}")).game_id)
        self.assertEqual(len(ids), 5)

    def test_disconnected_waiter_is_skipped(self) -> None:
        lobby = Lobby()
        ghost = FakeParticipant("ghost")
        lobby.join(ghost)
        ghost.connected = False
        live = FakeParticipant("live")
        self.assertIsNone(lobby.join(live))
        self.assertEqual(lobby.waiting_count(), 1)

    def test_remove_and_duplicate_join(self) -> None:
        lobby = Lobby()
        a = FakeParticipant("c1")
        lobby.join(a)
        self.assertIsNone(lobby.join(a))
        self.assertEqual(lobby.waiting_count(), 1)
        self.assertTrue(lobby.remove(a))
        self.assertFalse(lobby.remove(a))
        self.assertIsNone(lobby.join(FakeParticipant("c2")))

    def test_concurrent_joins_pair_each_player_once(self) -> None:
        lobby = Lobby()
        participants = [FakeParticipant(f"c{i}") for i in range(20)]
        games = []
        barrier = threading.Barrier(len(participants))

        def run(p: FakeParticipant) -> None:
            barrier.wait()
            game = lobby.join(p)
            if game is not None:
                games.append(game)

        threads = [threading.Thread(target=run, args=(p,)) for p in participants]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(len(games), 10)
        used = [pid for g in games for pid in g.players.values()]
        self.assertEqual(len(used), len(set(used)))
        self.assertEqual(lobby.waiting_count(), 0)


if __name__ == "__main__":
    unittest.main()
