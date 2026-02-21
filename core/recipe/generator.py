"""
recipe/generator.py — アライメント結果から recipe.json を生成する
"""

from __future__ import annotations

import numpy as np

from .schema import Recipe, Segment, Warning

_DEFAULT_CONFIDENCE_LOW = 0.5
_DEFAULT_CONFIDENCE_HIGH = 0.8
SEGMENT_DURATION = 2.0   # セグメント長（秒）
MAX_WARP_POINTS = 20     # セグメントあたりの最大ワープ点数


def _strength_from_confidence(
    confidence: float,
    confidence_low: float,
    confidence_high: float,
) -> tuple[float, float]:
    """
    confidence から (pitch_strength, time_strength) を計算する。

    高信頼 → 完全追従
    中信頼 → 比例して弱める
    低信頼 → グローバルキーシフトのみ（pitch_strength=0, time_strength 最小）
    """
    if confidence >= confidence_high:
        return 1.0, 1.0
    elif confidence >= confidence_low:
        ratio = (confidence - confidence_low) / (confidence_high - confidence_low)
        return float(ratio), float(ratio)
    else:
        return 0.0, 0.1


def _subsample(points: list, max_n: int) -> list:
    """等間隔にサブサンプリングする。"""
    if len(points) <= max_n:
        return points
    indices = np.round(np.linspace(0, len(points) - 1, max_n)).astype(int)
    return [points[i] for i in indices]


def _ref_f0_at_new_times(
    warp_map: list[tuple[float, float]],
    ref_times: np.ndarray,
    ref_f0: np.ndarray,
    query_times: np.ndarray,
) -> np.ndarray:
    """
    ワープマップを経由して、new_times に対応する ref_f0 値を返す。
    """
    if len(query_times) == 0 or len(warp_map) == 0:
        return np.zeros(len(query_times), dtype=np.float32)

    new_t = np.array([w[0] for w in warp_map], dtype=np.float32)
    ref_t = np.array([w[1] for w in warp_map], dtype=np.float32)

    # query_times → 対応する ref_times へ補間
    ref_t_interp = np.interp(query_times, new_t, ref_t)

    # ref_times → ref_f0 へ補間
    f0_at_query = np.interp(ref_t_interp, ref_times, ref_f0)
    return f0_at_query.astype(np.float32)


def generate(
    new_audio_duration: float,
    sample_rate: int,
    global_key_shift_semitones: float,
    alignment: dict,
    ref_f0: np.ndarray,
    ref_times: np.ndarray,
    new_f0: np.ndarray,
    new_times: np.ndarray,
    voiced_mask: np.ndarray,
    confidence_low: float = _DEFAULT_CONFIDENCE_LOW,
    confidence_high: float = _DEFAULT_CONFIDENCE_HIGH,
) -> Recipe:
    """
    アライメント結果と解析結果から Recipe を生成する。

    Parameters
    ----------
    new_audio_duration : float
        新規ボーカルの総秒数
    sample_rate : int
        サンプルレート
    global_key_shift_semitones : float
        グローバルキーシフト
    alignment : dict
        dtw_aligner.align() の返値
    ref_f0, ref_times : np.ndarray
        リファレンスボーカルの F0 と時刻
    new_f0, new_times : np.ndarray
        新規ボーカルの F0 と時刻
    voiced_mask : np.ndarray
        voiced_detector.detect_voiced() の返値（フレーム単位 bool）
    confidence_low : float
        低信頼度の閾値（デフォルト 0.5）
    confidence_high : float
        高信頼度の閾値（デフォルト 0.8）

    Returns
    -------
    Recipe
    """
    warp_map = alignment["warp_map"]
    confidence_per_frame = alignment["confidence_per_frame"]

    # voiced_mask が new_times と異なるフレーム数の場合にリサンプリングする
    if len(voiced_mask) != len(new_times):
        voiced_times = np.linspace(0.0, new_audio_duration, len(voiced_mask))
        voiced_mask = np.interp(new_times, voiced_times, voiced_mask.astype(np.float32)) > 0.5

    num_segments = max(1, int(np.ceil(new_audio_duration / SEGMENT_DURATION)))
    boundaries = np.linspace(0.0, new_audio_duration, num_segments + 1)

    segments: list[Segment] = []
    warnings: list[Warning] = []

    for idx in range(num_segments):
        t0 = float(boundaries[idx])
        t1 = float(boundaries[idx + 1])

        # このセグメントのフレームインデックス
        frame_mask = (new_times >= t0) & (new_times < t1)

        # 平均 confidence
        seg_conf = confidence_per_frame[frame_mask]
        confidence = float(np.mean(seg_conf)) if seg_conf.size > 0 else 0.5

        pitch_strength, time_strength = _strength_from_confidence(
            confidence, confidence_low, confidence_high
        )

        # ワープ点（このセグメント範囲に絞り込み・サブサンプル）
        seg_warp = [(nt, rt) for nt, rt in warp_map if t0 <= nt < t1]
        if not seg_warp:
            seg_warp = [(t0, t0), (t1, t1)]   # アライメントなし → 等倍
        else:
            seg_warp = _subsample(seg_warp, MAX_WARP_POINTS)

        # 目標ピッチカーブ（リファレンス F0 をワープマップ経由でマッピング）
        seg_new_times = new_times[frame_mask]
        seg_ref_f0 = _ref_f0_at_new_times(seg_warp, ref_times, ref_f0, seg_new_times)
        pitch_curve = [
            (float(t), float(hz))
            for t, hz in zip(seg_new_times, seg_ref_f0)
        ]
        if not pitch_curve:
            pitch_curve = [(t0, 0.0), (t1, 0.0)]
        else:
            pitch_curve = _subsample(pitch_curve, MAX_WARP_POINTS)

        # 無声保護フラグ: 有声フレームが 30% 未満のセグメントはピッチシフト対象外
        # （子音・ブレスなど主に無声の区間を保護する。混在セグメントは補正を継続）
        if frame_mask.any():
            voiced_ratio = float(voiced_mask[frame_mask].mean())
            protect = voiced_ratio < 0.3
        else:
            protect = True

        segments.append(Segment(
            t0=t0,
            t1=t1,
            time_warp_points=seg_warp,
            pitch_target_curve=pitch_curve,
            confidence=confidence,
            pitch_strength=pitch_strength,
            time_strength=time_strength,
            protect_unvoiced=protect,
        ))

        if confidence < confidence_low:
            warnings.append(Warning(
                t0=t0,
                t1=t1,
                reason="low_confidence",
                detail=f"confidence={confidence:.2f}。グローバルキーシフトのみ適用",
            ))

    return Recipe(
        version="0.1",
        sample_rate=sample_rate,
        global_key_shift_semitones=global_key_shift_semitones,
        segments=segments,
        warnings=warnings,
    )
