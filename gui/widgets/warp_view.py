"""
gui/widgets/warp_view.py — ワープマップ（タイミング補正）表示ウィジェット

対角線 = 等倍、折れ線 = 実際のアライメント
セグメント境界を縦線で表示。
"""

from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from PySide6.QtWidgets import QWidget, QVBoxLayout


class WarpView(QWidget):
    """new_time → ref_time の写像を折れ線で表示する。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()
        self._seg_lines: list[pg.InfiniteLine] = []

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._plot = pg.PlotWidget(title="Timing Warp (new → ref)")
        self._plot.setLabel("left", "Reference time", units="s")
        self._plot.setLabel("bottom", "New vocal time", units="s")
        self._plot.showGrid(x=True, y=True, alpha=0.2)

        # 等倍（対角線）
        self._diag = self._plot.plot(
            [], [], pen=pg.mkPen("#555555", width=1, style=pg.QtCore.Qt.DashLine),
        )
        # 実アライメント
        self._warp = self._plot.plot(
            [], [], pen=pg.mkPen("#f0a030", width=2),
        )

        layout.addWidget(self._plot)

    def set_warp_map(self, warp_map: list[tuple[float, float]], duration: float) -> None:
        if not warp_map:
            return

        new_t = np.array([p[0] for p in warp_map], dtype=np.float32)
        ref_t = np.array([p[1] for p in warp_map], dtype=np.float32)

        # 対角線
        d = np.array([0.0, duration], dtype=np.float32)
        self._diag.setData(d, d)

        # ワープ折れ線
        self._warp.setData(new_t, ref_t)

    def set_segments(self, boundaries: list[float]) -> None:
        """セグメント境界に縦線を描画する。"""
        for line in self._seg_lines:
            self._plot.removeItem(line)
        self._seg_lines.clear()

        for t in boundaries[1:-1]:  # 両端は省略
            line = pg.InfiniteLine(
                pos=t, angle=90,
                pen=pg.mkPen("#444466", width=1, style=pg.QtCore.Qt.DotLine),
            )
            self._plot.addItem(line)
            self._seg_lines.append(line)

    def clear(self) -> None:
        self._diag.setData([], [])
        self._warp.setData([], [])
        for line in self._seg_lines:
            self._plot.removeItem(line)
        self._seg_lines.clear()
