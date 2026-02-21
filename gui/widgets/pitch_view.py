"""
gui/widgets/pitch_view.py — ピッチカーブ表示ウィジェット

3本の曲線を重ねて表示:
  - リファレンス F0 (灰)
  - 新規ボーカル F0 (青)
  - 補正後 F0 (橙) ← recipe の pitch_target_curve から構築
"""

from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from PySide6.QtWidgets import QWidget, QVBoxLayout


class PitchView(QWidget):
    """F0 カーブを Hz → semitone(MIDI note) スケールで表示するウィジェット。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        pg.setConfigOptions(antialias=True, background="#1e1e1e", foreground="#cccccc")

        self._plot = pg.PlotWidget(title="Pitch (F0)")
        self._plot.setLabel("left", "Note", units="")
        self._plot.setLabel("bottom", "Time", units="s")
        self._plot.addLegend(offset=(10, 10))
        self._plot.showGrid(x=True, y=True, alpha=0.2)

        # 縦軸: MIDI ノート番号に対応する音名グリッド (C3〜C6)
        y_ticks = [(self._hz_to_note(440 * 2 ** ((n - 69) / 12)), self._note_name(n))
                   for n in range(48, 85, 12)]  # C3, C4, C5, C6
        self._plot.getAxis("left").setTicks([y_ticks])

        # 3本の曲線
        self._curve_ref = self._plot.plot(
            [], [], pen=pg.mkPen("#888888", width=1),
            name="リファレンス", connect="finite",
        )
        self._curve_new = self._plot.plot(
            [], [], pen=pg.mkPen("#4ea6ea", width=1.5),
            name="新規ボーカル", connect="finite",
        )
        self._curve_out = self._plot.plot(
            [], [], pen=pg.mkPen("#f0a030", width=2),
            name="補正後", connect="finite",
        )

        layout.addWidget(self._plot)

    # ------------------------------------------------------------------ #

    @staticmethod
    def _hz_to_note(hz: np.ndarray | float) -> np.ndarray | float:
        """Hz → MIDI ノート番号 (連続値)。0 は無声として NaN に変換。"""
        with np.errstate(divide="ignore", invalid="ignore"):
            result = np.where(hz > 0, 69 + 12 * np.log2(hz / 440.0), np.nan)
        return result

    @staticmethod
    def _note_name(midi: int) -> str:
        names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        return f"{names[midi % 12]}{midi // 12 - 1}"

    # ------------------------------------------------------------------ #

    def set_ref(self, times: np.ndarray, f0: np.ndarray) -> None:
        notes = self._hz_to_note(f0.astype(float))
        self._curve_ref.setData(times, notes)

    def set_new(self, times: np.ndarray, f0: np.ndarray) -> None:
        notes = self._hz_to_note(f0.astype(float))
        self._curve_new.setData(times, notes)

    def set_corrected(self, times: np.ndarray, f0: np.ndarray) -> None:
        """補正後 F0 をセット (recipe の pitch_target_curve から渡す)。"""
        notes = self._hz_to_note(f0.astype(float))
        self._curve_out.setData(times, notes)

    def set_corrected_from_recipe(self, recipe) -> None:
        """Recipe オブジェクトから補正後 F0 曲線を構築して表示する。"""
        all_t, all_hz = [], []
        for seg in recipe.segments:
            for t, hz in seg.pitch_target_curve:
                all_t.append(t)
                all_hz.append(hz)
        if all_t:
            t_arr = np.array(all_t, dtype=np.float32)
            hz_arr = np.array(all_hz, dtype=np.float32)
            self.set_corrected(t_arr, hz_arr)

    def clear(self) -> None:
        for curve in (self._curve_ref, self._curve_new, self._curve_out):
            curve.setData([], [])
