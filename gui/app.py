"""
gui/app.py — アプリケーションエントリーポイント
"""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> None:
    # プロジェクトルートを sys.path に追加（直接起動時）
    root = Path(__file__).parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    app.setApplicationName("Lyra")
    app.setOrganizationName("Lyra")

    # ダークテーマ
    app.setStyle("Fusion")
    _apply_dark_palette(app)

    from gui.main_window import MainWindow
    win = MainWindow()
    win.show()

    sys.exit(app.exec())


def _apply_dark_palette(app) -> None:
    from PySide6.QtGui import QPalette, QColor

    dark = QPalette()
    base   = QColor(30, 30, 30)
    text   = QColor(220, 220, 220)
    mid    = QColor(50, 50, 50)
    high   = QColor(70, 130, 200)
    bright = QColor(240, 240, 240)

    dark.setColor(QPalette.Window,          QColor(45, 45, 45))
    dark.setColor(QPalette.WindowText,      text)
    dark.setColor(QPalette.Base,            base)
    dark.setColor(QPalette.AlternateBase,   QColor(38, 38, 38))
    dark.setColor(QPalette.ToolTipBase,     QColor(60, 60, 60))
    dark.setColor(QPalette.ToolTipText,     text)
    dark.setColor(QPalette.Text,            text)
    dark.setColor(QPalette.Button,          mid)
    dark.setColor(QPalette.ButtonText,      text)
    dark.setColor(QPalette.BrightText,      bright)
    dark.setColor(QPalette.Link,            high)
    dark.setColor(QPalette.Highlight,       high)
    dark.setColor(QPalette.HighlightedText, QColor(255, 255, 255))

    app.setPalette(dark)


if __name__ == "__main__":
    main()
