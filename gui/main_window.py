"""
gui/main_window.py — lyra メインウィンドウ

レイアウト:
  ┌─ ツールバー (ファイル選択 / プリセット / Run) ───────────────┐
  │  ┌─ PitchView ─────────────────┐  ┌─ WarpView ──────────┐  │
  │  │  3本の F0 曲線              │  │  ワープマップ        │  │
  │  └─────────────────────────────┘  └────────────────────┘  │
  │  ┌─ SegmentPanel (スクロール) ─────────────────────────────┐  │
  │  │  セグメントスライダー + 再レンダリングボタン              │  │
  │  └────────────────────────────────────────────────────────┘  │
  │  ┌─ ステータスバー ────────────────────────────────────────┐  │
  └──────────────────────────────────────────────────────────────┘
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QFileDialog,
    QComboBox, QCheckBox, QSplitter, QProgressBar,
    QMessageBox, QDoubleSpinBox, QGroupBox,
)
from PySide6.QtCore import Qt

from .widgets.pitch_view import PitchView
from .widgets.warp_view import WarpView
from .widgets.segment_panel import SegmentPanel
from .worker import PipelineWorker, RerenderWorker, ExportWorker


PRESETS = {
    "light": {
        "description": "軽め", "confidence_low": 0.6, "confidence_high": 0.9, "band_radius": 0.08,
    },
    "standard": {
        "description": "標準", "confidence_low": 0.5, "confidence_high": 0.8, "band_radius": 0.10,
    },
    "strong": {
        "description": "強め", "confidence_low": 0.4, "confidence_high": 0.7, "band_radius": 0.12,
    },
}


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Lyra  —  Vocal Edit Automation")
        self.resize(1280, 800)

        self._result = None          # PipelineResult
        self._worker: PipelineWorker | None = None
        self._rerender_worker: RerenderWorker | None = None
        self._export_worker: ExportWorker | None = None

        self._setup_ui()

    # ------------------------------------------------------------------ #
    # UI 構築
    # ------------------------------------------------------------------ #

    def _setup_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        # ── ツールバー ──
        root.addWidget(self._build_toolbar())

        # ── メインエリア (splitter) ──
        splitter = QSplitter(Qt.Vertical)

        # 上段: ピッチビュー + ワープビュー (横並び)
        top_splitter = QSplitter(Qt.Horizontal)
        self._pitch_view = PitchView()
        self._warp_view = WarpView()
        top_splitter.addWidget(self._pitch_view)
        top_splitter.addWidget(self._warp_view)
        top_splitter.setSizes([700, 400])
        splitter.addWidget(top_splitter)

        # 下段: セグメントパネル
        self._segment_panel = SegmentPanel()
        self._segment_panel._recipe = None
        self._segment_panel.rerender_requested.connect(self._on_rerender)
        splitter.addWidget(self._segment_panel)

        splitter.setSizes([500, 220])
        root.addWidget(splitter)

        # ── ステータスバー ──
        sb = QHBoxLayout()
        self._progress = QProgressBar()
        self._progress.setRange(0, 7)
        self._progress.setValue(0)
        self._progress.setVisible(False)
        self._status_label = QLabel("ファイルを選択して Run を押してください")
        sb.addWidget(self._status_label, 1)
        sb.addWidget(self._progress)
        root.addLayout(sb)

    def _build_toolbar(self) -> QGroupBox:
        box = QGroupBox()
        layout = QHBoxLayout(box)
        layout.setContentsMargins(6, 4, 6, 4)

        # リファレンス
        layout.addWidget(QLabel("リファレンス:"))
        self._ref_edit = QLineEdit()
        self._ref_edit.setPlaceholderText("2mix または Vocal Stem")
        self._ref_edit.setMinimumWidth(200)
        layout.addWidget(self._ref_edit)
        btn_ref = QPushButton("…")
        btn_ref.setFixedWidth(28)
        btn_ref.clicked.connect(lambda: self._browse(self._ref_edit))
        layout.addWidget(btn_ref)

        # 新規ボーカル
        layout.addWidget(QLabel("新規ボーカル:"))
        self._vocal_edit = QLineEdit()
        self._vocal_edit.setPlaceholderText("ドライボーカル")
        self._vocal_edit.setMinimumWidth(200)
        layout.addWidget(self._vocal_edit)
        btn_vocal = QPushButton("…")
        btn_vocal.setFixedWidth(28)
        btn_vocal.clicked.connect(lambda: self._browse(self._vocal_edit))
        layout.addWidget(btn_vocal)

        # Stem チェック
        self._stem_chk = QCheckBox("Stem入力")
        self._stem_chk.setToolTip("リファレンスが Vocal Stem の場合はON（分離をスキップ）")
        layout.addWidget(self._stem_chk)

        # プリセット
        layout.addWidget(QLabel("プリセット:"))
        self._preset_combo = QComboBox()
        for key, v in PRESETS.items():
            self._preset_combo.addItem(f"{key} ({v['description']})", key)
        self._preset_combo.setCurrentIndex(1)  # standard
        layout.addWidget(self._preset_combo)

        # キーシフト
        layout.addWidget(QLabel("キーシフト:"))
        self._keyshift_spin = QDoubleSpinBox()
        self._keyshift_spin.setRange(-12.0, 12.0)
        self._keyshift_spin.setSingleStep(1.0)
        self._keyshift_spin.setDecimals(1)
        self._keyshift_spin.setSpecialValueText("自動")
        self._keyshift_spin.setValue(self._keyshift_spin.minimum())  # 自動
        self._keyshift_spin.setFixedWidth(72)
        layout.addWidget(self._keyshift_spin)

        layout.addStretch()

        # Run ボタン
        self._run_btn = QPushButton("▶  Run")
        self._run_btn.setFixedHeight(32)
        self._run_btn.setStyleSheet("QPushButton { font-weight: bold; padding: 0 16px; }")
        self._run_btn.clicked.connect(self._on_run)
        layout.addWidget(self._run_btn)

        # Export ボタン
        self._export_btn = QPushButton("Export WAV")
        self._export_btn.setEnabled(False)
        self._export_btn.setFixedHeight(32)
        self._export_btn.clicked.connect(self._on_export)
        layout.addWidget(self._export_btn)

        return box

    # ------------------------------------------------------------------ #
    # ファイルブラウザ
    # ------------------------------------------------------------------ #

    def _browse(self, edit: QLineEdit) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "音声ファイルを選択", "",
            "Audio Files (*.wav *.flac *.aiff *.aif);;All Files (*)",
        )
        if path:
            edit.setText(path)

    # ------------------------------------------------------------------ #
    # Run
    # ------------------------------------------------------------------ #

    def _on_run(self) -> None:
        ref = self._ref_edit.text().strip()
        vocal = self._vocal_edit.text().strip()

        if not ref or not Path(ref).exists():
            QMessageBox.warning(self, "エラー", "リファレンスファイルが見つかりません")
            return
        if not vocal or not Path(vocal).exists():
            QMessageBox.warning(self, "エラー", "新規ボーカルファイルが見つかりません")
            return

        preset_key = self._preset_combo.currentData()
        preset = PRESETS[preset_key]

        ks_val = self._keyshift_spin.value()
        key_shift = None if ks_val == self._keyshift_spin.minimum() else ks_val

        # UI を処理中状態に
        self._run_btn.setEnabled(False)
        self._export_btn.setEnabled(False)
        self._progress.setVisible(True)
        self._progress.setValue(0)
        self._pitch_view.clear()
        self._warp_view.clear()

        self._worker = PipelineWorker(
            ref_path=ref,
            vocal_path=vocal,
            is_stem=self._stem_chk.isChecked(),
            preset=preset,
            key_shift_override=key_shift,
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_progress(self, step: int, total: int, msg: str) -> None:
        self._progress.setMaximum(total)
        self._progress.setValue(step)
        self._status_label.setText(f"[{step}/{total}] {msg}")

    def _on_finished(self, result) -> None:
        self._result = result
        self._worker = None  # 参照を解放して GC を許可
        self._run_btn.setEnabled(True)
        self._progress.setVisible(False)
        self._status_label.setText(
            f"完了 — セグメント数: {len(result.recipe.segments)}  "
            f"warnings: {len(result.recipe.warnings)}"
        )

        # ピッチビュー更新
        self._pitch_view.set_ref(result.ref_times, result.ref_f0)
        self._pitch_view.set_new(result.new_times, result.new_f0)
        self._pitch_view.set_corrected_from_recipe(result.recipe)

        # ワープビュー更新
        duration = len(result.new_audio) / result.sample_rate
        self._warp_view.set_warp_map(result.alignment["warp_map"], duration)

        # セグメントパネル更新
        self._segment_panel.bind_recipe(result.recipe)

        self._export_btn.setEnabled(True)

    def _on_error(self, msg: str) -> None:
        self._worker = None  # 参照を解放
        self._run_btn.setEnabled(True)
        self._progress.setVisible(False)
        self._status_label.setText("エラーが発生しました")
        QMessageBox.critical(self, "パイプラインエラー", msg)

    # ------------------------------------------------------------------ #
    # 再レンダリング
    # ------------------------------------------------------------------ #

    def _on_rerender(self) -> None:
        if self._result is None:
            return

        self._status_label.setText("再レンダリング中…")
        self._segment_panel._rerender_btn.setEnabled(False)

        self._rerender_worker = RerenderWorker(
            new_audio=self._result.new_audio,
            sample_rate=self._result.sample_rate,
            recipe=self._result.recipe,
            new_f0=self._result.new_f0,
            new_times=self._result.new_times,
        )
        self._rerender_worker.finished.connect(self._on_rerender_done)
        self._rerender_worker.error.connect(self._on_error)
        self._rerender_worker.start()

    def _on_rerender_done(self, output_audio: np.ndarray) -> None:
        self._result.output_audio = output_audio
        self._rerender_worker = None  # 参照を解放
        self._segment_panel._rerender_btn.setEnabled(True)
        self._status_label.setText("再レンダリング完了")
        # ピッチ補正後曲線を再描画
        self._pitch_view.set_corrected_from_recipe(self._result.recipe)

    # ------------------------------------------------------------------ #
    # Export
    # ------------------------------------------------------------------ #

    def _on_export(self) -> None:
        if self._result is None:
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "WAV として保存", "edited_vocal.wav",
            "WAV Files (*.wav)",
        )
        if not path:
            return

        recipe_path = str(Path(path).with_suffix(".json"))

        self._export_btn.setEnabled(False)
        self._status_label.setText("保存中…")

        self._export_worker = ExportWorker(
            wav_path=path,
            recipe_path=recipe_path,
            output_audio=self._result.output_audio,
            sample_rate=self._result.sample_rate,
            recipe=self._result.recipe,
        )
        self._export_worker.finished.connect(self._on_export_done)
        self._export_worker.error.connect(self._on_export_error)
        self._export_worker.start()

    def _on_export_done(self, wav_path: str) -> None:
        recipe_path = str(Path(wav_path).with_suffix(".json"))
        self._export_worker = None  # 参照を解放
        self._export_btn.setEnabled(True)
        self._status_label.setText(f"保存完了: {wav_path}")
        QMessageBox.information(self, "保存完了",
                                f"WAV: {wav_path}\nrecipe: {recipe_path}")

    def _on_export_error(self, msg: str) -> None:
        self._export_worker = None  # 参照を解放
        self._export_btn.setEnabled(True)
        self._status_label.setText("保存に失敗しました")
        QMessageBox.critical(self, "保存エラー", msg)
