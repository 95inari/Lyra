"""
alignment/dtw_aligner.py — DTW によるリファレンス↔新規ボーカルのアライメント

dtw-python + Sakoe-Chiba バンド制約でメモリ使用量を抑制する。
5分曲 (100fps) で約 3.6GB になる制約なしの DTW に対し、
バンド幅 10% で約 360MB に削減する。
"""

from __future__ import annotations

import numpy as np
from dtw import dtw


# ---- 特徴量計算 --------------------------------------------------------

def _f0_to_cents(f0: np.ndarray) -> np.ndarray:
    """F0 (Hz) を A4=0 基準の cents に変換。無声フレームは 0。"""
    cents = np.zeros_like(f0, dtype=np.float32)
    voiced = f0 > 0
    cents[voiced] = 1200.0 * np.log2(f0[voiced] / 440.0)
    return cents


def _build_features(
    f0: np.ndarray,
    onsets: np.ndarray,
    times: np.ndarray,
) -> np.ndarray:
    """
    DTW 用特徴行列を構築する。

    特徴: [正規化 F0 (cents), オンセット指示関数]
    shape: (frames, 2)
    """
    cents = _f0_to_cents(f0)

    # 正規化（有声区間の統計で）
    voiced = f0 > 0
    if voiced.any() and cents[voiced].std() > 0:
        cents[voiced] = (cents[voiced] - cents[voiced].mean()) / cents[voiced].std()

    # オンセット指示関数（オンセット近傍フレームに 1.0）
    onset_indicator = np.zeros(len(times), dtype=np.float32)
    for t in onsets:
        idx = int(np.searchsorted(times, t))
        for offset in (-1, 0, 1):
            i = idx + offset
            if 0 <= i < len(onset_indicator):
                onset_indicator[i] = 1.0

    return np.column_stack([cents, onset_indicator]).astype(np.float32)


# ---- メインアライメント関数 ---------------------------------------------

def align(
    ref_f0: np.ndarray,
    ref_times: np.ndarray,
    ref_onsets: np.ndarray,
    new_f0: np.ndarray,
    new_times: np.ndarray,
    new_onsets: np.ndarray,
    band_radius: float = 0.1,
) -> dict:
    """
    新規ボーカルをリファレンスに DTW でアライメントする。

    Parameters
    ----------
    ref_f0, new_f0 : np.ndarray
        F0 カーブ (Hz)、0 は無声
    ref_times, new_times : np.ndarray
        各フレームの時刻（秒）
    ref_onsets, new_onsets : np.ndarray
        オンセット時刻（秒）
    band_radius : float
        Sakoe-Chiba バンド幅（全フレーム数に対する比率）

    Returns
    -------
    dict with keys:
        warp_map : list[tuple[float, float]]
            (new_time, ref_time) の対応点リスト
        confidence_per_frame : np.ndarray
            新規ボーカルの各フレームの信頼度 (0〜1)
        new_times : np.ndarray
            新規ボーカルのフレーム時刻
    """
    ref_feat = _build_features(ref_f0, ref_onsets, ref_times)
    new_feat = _build_features(new_f0, new_onsets, new_times)

    n_ref, n_new = len(ref_feat), len(new_feat)

    # HEAD-ALIGNED PARTIAL MATCH:
    # リファレンスが新規より大幅に長い場合（フル曲 vs 一部素材）、
    # Sakoe-Chiba 対角線が new フレームを ref 全体に引き伸ばして誤アライメントを起こす。
    # 両素材は t=0 で頭出し済みの前提で、ref を new と同尺 + マージンに切り詰める。
    ref_margin = max(10, int(band_radius * n_new))
    if n_ref > n_new + ref_margin:
        trunc = n_new + ref_margin
        ref_feat = ref_feat[:trunc]
        ref_times = ref_times[:trunc]
        n_ref = trunc

    window_size = max(10, int(band_radius * max(n_ref, n_new)))

    alignment = dtw(
        new_feat,
        ref_feat,
        window_type="sakoechiba",
        window_args={"window_size": window_size},
        keep_internals=True,
    )

    # ワープマップ: (new_time, ref_time) の対応点
    warp_map: list[tuple[float, float]] = []
    seen_new = set()
    for i, j in zip(alignment.index1, alignment.index2):
        if i not in seen_new and i < n_new and j < n_ref:
            warp_map.append((float(new_times[i]), float(ref_times[j])))
            seen_new.add(i)

    # 信頼度: DTW ローカルコストの逆数（コストが低い = 一致度が高い）
    cost_matrix = alignment.localCostMatrix
    costs = np.array([
        cost_matrix[i, j]
        for i, j in zip(alignment.index1, alignment.index2)
        if i < cost_matrix.shape[0] and j < cost_matrix.shape[1]
    ], dtype=np.float32)

    max_cost = costs.max() if costs.size > 0 else 1.0
    raw_confidence = 1.0 - (costs / (max_cost + 1e-8))

    # new_times の全フレームに confidence を割り当て
    confidence_per_frame = np.zeros(n_new, dtype=np.float32)
    for k, i in enumerate(alignment.index1):
        if i < n_new and k < len(raw_confidence):
            confidence_per_frame[i] = max(
                confidence_per_frame[i], raw_confidence[k]
            )

    return {
        "warp_map": warp_map,
        "confidence_per_frame": confidence_per_frame,
        "new_times": new_times,
    }
