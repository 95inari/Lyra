"""
renderer/rubberband_renderer.py — pyrubberband でタイムストレッチ・ピッチシフトを適用する

依存:
  brew install rubberband      # CLI バイナリ
  pip install pyrubberband     # Python ラッパー
"""

from __future__ import annotations

import shutil
import numpy as np
import pyrubberband as pyrb

from ..recipe.schema import Recipe, Segment

# モジュールロード時に一度だけ rubberband の存在を確認する
if shutil.which("rubberband") is None:
    raise RuntimeError(
        "rubberband コマンドが見つかりません。\n"
        "  macOS: brew install rubberband\n"
        "  Linux: apt install rubberband-cli または pip install rubberband\n"
        "  Windows: https://breakfastquay.com/rubberband/ からバイナリを取得してください"
    )


def render(
    audio: np.ndarray,
    sr: int,
    recipe: Recipe,
    new_f0: np.ndarray | None = None,
    new_times: np.ndarray | None = None,
) -> np.ndarray:
    """
    Recipe を新規ボーカルに適用し、補正済み音声を返す。

    処理順序:
    1. グローバルキーシフト（全体に一括適用）
    2. セグメントごとのタイムストレッチ
    3. セグメントごとのピッチシフト（new_f0 が渡された場合のみ）

    Parameters
    ----------
    audio : np.ndarray
        新規ドライボーカル (samples,) float32
    sr : int
        サンプルレート
    recipe : Recipe
    new_f0 : np.ndarray | None
        新規ボーカルの F0 カーブ (Hz)。None の場合はセグメントピッチをスキップ。
    new_times : np.ndarray | None
        new_f0 の各フレーム時刻（秒）

    Returns
    -------
    np.ndarray
        補正済みモノラル音声 (samples,)
    """
    audio = audio.astype(np.float64)  # pyrubberband は float64 を期待

    # --- 1. グローバルキーシフト ---
    if abs(recipe.global_key_shift_semitones) > 0.01:
        audio = pyrb.pitch_shift(audio, sr, n_steps=recipe.global_key_shift_semitones)
        # F0 カーブも同じだけシフト（per-segment 比較に使う）
        if new_f0 is not None:
            shift_ratio = 2.0 ** (recipe.global_key_shift_semitones / 12.0)
            new_f0 = np.where(new_f0 > 0, new_f0 * shift_ratio, 0.0)

    # --- 2 & 3. セグメント処理 ---
    output_chunks: list[np.ndarray] = []

    for seg in recipe.segments:
        s_start = int(seg.t0 * sr)
        s_end = min(int(seg.t1 * sr), len(audio))
        chunk = audio[s_start:s_end]

        if len(chunk) == 0:
            continue

        chunk = _apply_segment(chunk, sr, seg, new_f0, new_times)
        output_chunks.append(chunk)

    if not output_chunks:
        return audio.astype(np.float32)

    return np.concatenate(output_chunks).astype(np.float32)


def _apply_segment(
    chunk: np.ndarray,
    sr: int,
    seg: Segment,
    new_f0: np.ndarray | None,
    new_times: np.ndarray | None,
) -> np.ndarray:
    """セグメント単位でタイムストレッチ + ピッチシフトを適用する。"""

    # ---- タイムストレッチ ----
    if seg.time_strength > 0.05 and len(seg.time_warp_points) >= 2:
        warp = np.array(seg.time_warp_points, dtype=np.float64)
        in_dur = warp[-1, 0] - warp[0, 0]
        out_dur = warp[-1, 1] - warp[0, 1]

        if in_dur > 0 and out_dur > 0:
            full_ratio = out_dur / in_dur
            # identity と full_ratio を time_strength で線形補間
            effective_ratio = 1.0 + seg.time_strength * (full_ratio - 1.0)
            effective_ratio = float(np.clip(effective_ratio, 0.5, 2.0))

            if abs(effective_ratio - 1.0) > 0.01:
                # pyrubberband: rate > 1.0 = 遅く（長く）、rate < 1.0 = 速く（短く）
                chunk = pyrb.time_stretch(chunk, sr, rate=effective_ratio)

    # ---- ピッチシフト ----
    # protect_unvoiced=True のとき、無声区間（子音・ブレス）へのピッチシフトを無効化する
    pitch_strength_eff = 0.0 if seg.protect_unvoiced else seg.pitch_strength
    if pitch_strength_eff > 0.01:
        semitones = _compute_pitch_shift(seg, new_f0, new_times)
        semitones_eff = float(np.clip(semitones * pitch_strength_eff, -12.0, 12.0))
        if abs(semitones_eff) > 0.05:
            chunk = pyrb.pitch_shift(chunk, sr, n_steps=semitones_eff)

    return chunk


def _compute_pitch_shift(
    seg: Segment,
    new_f0: np.ndarray | None,
    new_times: np.ndarray | None,
) -> float:
    """
    このセグメントで必要なピッチシフト量（セミトーン）を計算する。

    目標ピッチ中央値 / 現在ピッチ中央値 から導く。
    """
    target_hz = np.array([hz for _, hz in seg.pitch_target_curve if hz > 0])
    if len(target_hz) == 0:
        return 0.0

    if new_f0 is None or new_times is None:
        return 0.0

    frame_mask = (new_times >= seg.t0) & (new_times < seg.t1)
    seg_f0 = new_f0[frame_mask]
    voiced = seg_f0[seg_f0 > 0]

    if len(voiced) == 0:
        return 0.0

    current_median = float(np.median(voiced))
    target_median = float(np.median(target_hz))

    if current_median <= 0:
        return 0.0

    semitones = 12.0 * np.log2(target_median / current_median)
    return float(np.clip(semitones, -24.0, 24.0))
