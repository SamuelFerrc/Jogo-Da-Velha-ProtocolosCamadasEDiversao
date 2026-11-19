import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEventLoop, QObject, QTimer, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

from interface.client_window import ClientBackend
from interface.qt_common import QML_DIR
from interface.server_window import ServerBackend
from shared.protocol import make_message
from shared.transport import connect_to_server


class QtQuickInterfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        QQuickStyle.setStyle("Basic")
        cls.app = QGuiApplication.instance() or QGuiApplication([])

    def wait_for_layout(self, milliseconds: int) -> None:
        loop = QEventLoop()
        QTimer.singleShot(milliseconds, loop.quit)
        loop.exec()
        self.app.processEvents()

    def load_qml(self, backend: QObject, filename: str) -> QQmlApplicationEngine:
        engine = QQmlApplicationEngine()
        engine.rootContext().setContextProperty("backend", backend)
        engine.load(QUrl.fromLocalFile(str(QML_DIR / filename)))
        self.assertTrue(engine.rootObjects(), f"{filename} não carregou")
        self.app.processEvents()
        return engine

    def wait_until(self, predicate, *, timeout_ms: int = 2000) -> bool:
        for _ in range(max(1, timeout_ms // 25)):
            if predicate():
                return True
            self.wait_for_layout(25)
        return predicate()

    def test_client_drawer_compresses_layout_and_preserves_square_board(self) -> None:
        backend = ClientBackend("127.0.0.1", 9, console_enabled=False)
        engine = self.load_qml(backend, "ClientWindow.qml")
        root = engine.rootObjects()[0]
        drawer = root.findChild(QObject, "terminalDrawer")
        board = root.findChild(QObject, "officialBoard")
        main_layout = root.findChild(QObject, "mainLayout")
        self.assertIsNotNone(drawer)
        self.assertIsNotNone(board)
        self.assertIsNotNone(main_layout)

        initial_board = float(board.property("width"))
        initial_main = float(main_layout.property("height"))
        collapsed_drawer = float(drawer.property("height"))

        drawer.setProperty("open", True)
        self.wait_for_layout(450)
        compressed_board = float(board.property("width"))
        compressed_main = float(main_layout.property("height"))
        expanded_drawer = float(drawer.property("height"))

        self.assertGreater(expanded_drawer, collapsed_drawer)
        self.assertLess(compressed_main, initial_main)
        self.assertLess(compressed_board, initial_board)
        self.assertAlmostEqual(
            compressed_board,
            float(board.property("height")),
            places=2,
        )

        drawer.setProperty("open", False)
        self.wait_for_layout(350)
        self.assertGreater(float(board.property("width")), compressed_board)
        self.assertAlmostEqual(
            float(drawer.property("height")),
            collapsed_drawer,
            places=1,
        )

        backend.shutdown()
        root.setProperty("visible", False)
        engine.deleteLater()
        self.wait_for_layout(10)

    def test_server_qml_starts_the_real_server_backend(self) -> None:
        backend = ServerBackend("127.0.0.1", 0, console_enabled=False)
        self.assertFalse(backend._poll_timer.isActive())
        engine = self.load_qml(backend, "ServerWindow.qml")
        root = engine.rootObjects()[0]
        self.assertTrue(backend.serverRunning)
        self.assertTrue(backend._poll_timer.isActive())
        self.assertIn("Escutando em 127.0.0.1:", backend.addressLabel)

        backend.shutdown()
        root.setProperty("visible", False)
        engine.deleteLater()
        self.wait_for_layout(10)

    def test_server_qml_updates_sessions_and_active_game(self) -> None:
        backend = ServerBackend("127.0.0.1", 0, console_enabled=False)
        engine = self.load_qml(backend, "ServerWindow.qml")
        root = engine.rootObjects()[0]
        sessions_list = root.findChild(QObject, "sessionsList")
        game_summary = root.findChild(QObject, "gameSummaryText")
        self.assertIsNotNone(sessions_list)
        self.assertIsNotNone(game_summary)
        self.assertIsNotNone(backend.server)

        first = connect_to_server(*backend.server.address, timeout=2)
        second = connect_to_server(*backend.server.address, timeout=2)
        first.set_timeout(2)
        second.set_timeout(2)
        try:
            for channel in (first, second):
                channel.send_message(make_message("HELLO"))
                self.assertEqual(channel.receive_message()["type"], "WELCOME")

            first.send_message(make_message("JOIN"))
            self.assertEqual(first.receive_message()["type"], "WAITING")
            second.send_message(make_message("JOIN"))
            for channel in (first, second):
                self.assertEqual(channel.receive_message()["type"], "START")
                self.assertEqual(channel.receive_message()["type"], "BOARD")

            updated = self.wait_until(
                lambda: backend.sessionCount == 2
                and backend.gameCount == 1
                and int(sessions_list.property("count")) == 2
                and str(game_summary.property("text")).startswith("g1 · revisão 0")
            )
            self.assertTrue(updated, "painel do servidor não refletiu a partida ativa")
        finally:
            first.close()
            second.close()
            backend.shutdown()
            root.setProperty("visible", False)
            engine.deleteLater()
            self.wait_for_layout(10)


if __name__ == "__main__":
    unittest.main()
