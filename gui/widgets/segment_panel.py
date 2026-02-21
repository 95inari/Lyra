"""
gui/widgets/segment_panel.py — セグメント強度スライダーパネル

各セグメントに pitch_strength / time_strength スライダーを並べる。
スライダー変更 → シグナル経由で再レンダリングをトリガー。
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QScrollArea, QVBoxLayout, QHBoxLayout,
    QLabel, QSlider, QFrame, QPushButton,
)
from PySide6.QtCore import Qt, Signal


class SegmentRow(QWidget):
    """1 セグメント分の行 (pitch / time スライダー + confidence バッジ)。"""

    changed = Signal(int, float, float)  # (seg_idx, pitch_strength, time_strength)

    def __init__(self, idx: int, t0: float, t1: float,
                 confidence: float, pitch_strength: float, time_strength: float,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._idx = idx
        self._setup_ui(idx, t0, t1, confidence, pitch_strength, time_strength)

    def _setup_ui(self, idx, t0, t1, conf, ps, ts) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)

        # ラベル
        lbl = QLabel(f"Seg {idx+1}  {t0:.1f}–{t1:.1f}s")
        lbl.setFixedWidth(130)
        layout.addWidget(lbl)

        # Confidence バッジ
        color = "#44bb44" if conf >= 0.8 else ("#eeaa22" if conf >= 0.5 else "#cc4444")
        badge = QLabel(f"conf {conf:.2f}")
        badge.setStyleSheet(f"color:{color}; font-size:11px;")
        badge.setFixedWidth(70)
        layout.addWidget(badge)

        # Pitch strength
        layout.addWidget(QLabel("Pitch:"))
        self._ps_slider = QSlider(Qt.Horizontal)
        self._ps_slider.setRange(0, 100)
        self._ps_slider.setValue(int(ps * 100))
        self._ps_slider.setFixedWidth(100)
        self._ps_label = QLabel(f"{ps:.2f}")
        self._ps_label.setFixedWidth(32)
        self._ps_slider.valueChanged.connect(self._on_change)
        layout.addWidget(self._ps_slider)
        layout.addWidget(self._ps_label)

        # Time strength
        layout.addWidget(QLabel("Time:"))
        self._ts_slider = QSlider(Qt.Horizontal)
        self._ts_slider.setRange(0, 100)
        self._ts_slider.setValue(int(ts * 100))
        self._ts_slider.setFixedWidth(100)
        self._ts_label = QLabel(f"{ts:.2f}")
        self._ts_label.setFixedWidth(32)
        self._ts_slider.valueChanged.connect(self._on_change)
        layout.addWidget(self._ts_slider)
        layout.addWidget(self._ts_label)

        layout.addStretch()

    def _on_change(self) -> None:
        ps = self._ps_slider.value() / 100.0
        ts = self._ts_slider.value() / 100.0
        self._ps_label.setText(f"{ps:.2f}")
        self._ts_label.setText(f"{ts:.2f}")
        self.changed.emit(self._idx, ps, ts)

    def pitch_strength(self) -> float:
        return self._ps_slider.value() / 100.0

    def time_strength(self) -> float:
        return self._ts_slider.value() / 100.0


class SegmentPanel(QWidget):
    """スクロール可能なセグメントスライダー一覧 + 再レンダリングボタン。"""

    rerender_requested = Signal()  # 再レンダリング要求

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._rows: list[SegmentRow] = []
        self._recipe = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        # ヘッダー
        header = QHBoxLayout()
        header.addWidget(QLabel("セグメント調整"))
        header.addStretch()
        self._rerender_btn = QPushButton("再レンダリング")
        self._rerender_btn.setEnabled(False)
        self._rerender_btn.clicked.connect(self.rerender_requested)
        header.addWidget(self._rerender_btn)
        outer.addLayout(header)

        # スクロールエリア
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        self._container = QWidget()
        self._inner = QVBoxLayout(self._container)
        self._inner.setSpacing(1)
        self._inner.addStretch()
        scroll.setWidget(self._container)

        outer.addWidget(scroll)

    def load_recipe(self, recipe) -> None:
        """Recipe オブジェクトからセグメント行を生成する。"""
        # 既存クリア
        for row in self._rows:
            row.setParent(None)
        self._rows.clear()

        # stretch を一旦除去
        self._inner.takeAt(self._inner.count() - 1)

        for idx, seg in enumerate(recipe.segments):
            row = SegmentRow(
                idx=idx,
                t0=seg.t0, t1=seg.t1,
                confidence=seg.confidence,
                pitch_strength=seg.pitch_strength,
                time_strength=seg.time_strength,
            )
            row.changed.connect(self._on_row_changed)
            self._inner.addWidget(row)
            self._rows.append(row)

        self._inner.addStretch()
        self._rerender_btn.setEnabled(True)

    def _on_row_changed(self, idx: int, ps: float, ts: float) -> None:
        """スライダー変更時に Recipe を更新する（参照を保持）。"""
        if self._recipe is not None:
            seg = self._recipe.segments[idx]
            seg.pitch_strength = ps
            seg.time_strength = ts

    def bind_recipe(self, recipe) -> None:
        """Recipe の参照を保持してスライダー変更を直接反映させる。"""
        self._recipe = recipe
        self.load_recipe(recipe)

    def _recipe_attr_init(self) -> None:
        self._recipe = None
