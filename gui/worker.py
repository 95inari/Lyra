"""
gui/worker.py — パイプライン処理を別スレッドで実行する QThread Worker
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from PySide6.QtCore import QThread, Signal


@dataclass
class PipelineResult:
    ref_f0: np.ndarray
    ref_times: np.ndarray
    new_f0: np.ndarray
    new_times: np.ndarray
    new_audio: np.ndarray
    sample_rate: int
    alignment: dict
    recipe: object          # core.recipe.schema.Recipe
    output_audio: np.ndarray


class PipelineWorker(QThread):
    """
    メインスレッドをブロックせずにパイプラインを実行する。

    シグナル:
      progress(step: int, total: int, message: str)
      finished(result: PipelineResult)
      error(message: str)
    """

    progress = Signal(int, int, str)
    finished = Signal(object)
    error = Signal(str)

    def __init__(
        self,
        ref_path: str,
        vocal_path: str,
        is_stem: bool,
        preset: dict,
        key_shift_override: float | None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.ref_path = ref_path
        self.vocal_path = vocal_path
        self.is_stem = is_stem
        self.preset = preset
        self.key_shift_override = key_shift_override

    def run(self) -> None:
        try:
            self._run_pipeline()
        except Exception as e:
            import traceback
            self.error.emit(f"{type(e).__name__}: {e}\n\n{traceback.format_exc()}")

    def _run_pipeline(self) -> None:
        from core.audio_io import load
        from core.separation.demucs_wrapper import separate_vocal
        from core.pitch.rmvpe_wrapper import estimate_f0
        from core.onset.onset_detector import detect_onsets
        from core.onset.voiced_detector import detect_voiced
        from core.key_detector import detect_key_shift
        from core.alignment.dtw_aligner import align
        from core.recipe.generator import generate
        from core.renderer.rubberband_renderer import render

        TOTAL = 7
        TARGET_SR = 44100

        # Step 1
        self.progress.emit(1, TOTAL, "音声ファイルを読み込んでいます…")
        ref_audio, _ = load(self.ref_path, target_sr=TARGET_SR)
        new_audio, _ = load(self.vocal_path, target_sr=TARGET_SR)

        # Step 2
        if self.is_stem:
            self.progress.emit(2, TOTAL, "Stem 入力 — 分離をスキップ")
            ref_vocal = ref_audio
        else:
            self.progress.emit(2, TOTAL, "ボーカル分離中 (Demucs)…")
            ref_vocal = separate_vocal(ref_audio, TARGET_SR)

        # Step 3
        self.progress.emit(3, TOTAL, "F0 解析中 (RMVPE)…")
        ref_f0, ref_times = estimate_f0(ref_vocal, TARGET_SR)
        new_f0, new_times = estimate_f0(new_audio, TARGET_SR)

        # Step 4
        self.progress.emit(4, TOTAL, "オンセット・有声区間検出中…")
        ref_onsets = detect_onsets(ref_vocal, TARGET_SR)
        new_onsets = detect_onsets(new_audio, TARGET_SR)
        voiced_mask = detect_voiced(new_audio, TARGET_SR)

        # Step 5
        self.progress.emit(5, TOTAL, "キーシフト推定中…")
        if self.key_shift_override is not None:
            key_shift = float(self.key_shift_override)
        else:
            key_shift = detect_key_shift(ref_f0, new_f0)

        # Step 6
        self.progress.emit(6, TOTAL, "DTW アライメント中…")
        alignment = align(
            ref_f0=ref_f0, ref_times=ref_times, ref_onsets=ref_onsets,
            new_f0=new_f0, new_times=new_times, new_onsets=new_onsets,
            band_radius=self.preset["band_radius"],
        )

        # Step 7
        self.progress.emit(7, TOTAL, "レシピ生成・レンダリング中…")

        recipe = generate(
            new_audio_duration=len(new_audio) / TARGET_SR,
            sample_rate=TARGET_SR,
            global_key_shift_semitones=key_shift,
            alignment=alignment,
            ref_f0=ref_f0, ref_times=ref_times,
            new_f0=new_f0, new_times=new_times,
            voiced_mask=voiced_mask,
            confidence_low=self.preset["confidence_low"],
            confidence_high=self.preset["confidence_high"],
        )

        output_audio = render(new_audio, TARGET_SR, recipe,
                              new_f0=new_f0, new_times=new_times)

        result = PipelineResult(
            ref_f0=ref_f0, ref_times=ref_times,
            new_f0=new_f0, new_times=new_times,
            new_audio=new_audio,
            sample_rate=TARGET_SR,
            alignment=alignment,
            recipe=recipe,
            output_audio=output_audio,
        )
        self.finished.emit(result)


class RerenderWorker(QThread):
    """
    セグメントスライダー変更後の再レンダリング専用 Worker。
    recipe は既にスライダー値が反映済みの状態で渡す。
    """

    finished = Signal(object)   # np.ndarray (output audio)
    error = Signal(str)

    def __init__(self, new_audio: np.ndarray, sample_rate: int,
                 recipe, new_f0: np.ndarray, new_times: np.ndarray,
                 parent=None) -> None:
        super().__init__(parent)
        self.new_audio = new_audio
        self.sample_rate = sample_rate
        self.recipe = recipe
        self.new_f0 = new_f0
        self.new_times = new_times

    def run(self) -> None:
        try:
            from core.renderer.rubberband_renderer import render
            output = render(self.new_audio, self.sample_rate, self.recipe,
                            new_f0=self.new_f0, new_times=self.new_times)
            self.finished.emit(output)
        except Exception as e:
            import traceback
            self.error.emit(f"{type(e).__name__}: {e}\n\n{traceback.format_exc()}")


class ExportWorker(QThread):
    """
    WAV ファイルと recipe.json の書き出しを別スレッドで実行する。
    大きなファイルの書き込みで UI がフリーズするのを防ぐ。
    """

    finished = Signal(str)   # 保存した WAV パス
    error = Signal(str)

    def __init__(self, wav_path: str, recipe_path: str,
                 output_audio, sample_rate: int, recipe,
                 parent=None) -> None:
        super().__init__(parent)
        self.wav_path = wav_path
        self.recipe_path = recipe_path
        self.output_audio = output_audio
        self.sample_rate = sample_rate
        self.recipe = recipe

    def run(self) -> None:
        try:
            from core.audio_io import save
            save(self.wav_path, self.output_audio, self.sample_rate)
            self.recipe.save(self.recipe_path)
            self.finished.emit(self.wav_path)
        except Exception as e:
            import traceback
            self.error.emit(f"{type(e).__name__}: {e}\n\n{traceback.format_exc()}")
