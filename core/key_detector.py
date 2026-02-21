"""
key_detector.py — リファレンスと新規ボーカルの F0 中央値比較によるキーシフト自動推定
"""

import numpy as np


def detect_key_shift(ref_f0: np.ndarray, new_f0: np.ndarray) -> float:
    """
    リファレンスと新規ボーカルの F0 中央値を比較してセミトーン差を推定する。

    Parameters
    ----------
    ref_f0 : np.ndarray
        リファレンスボーカルの F0 カーブ (Hz)。0 は無声フレーム。
    new_f0 : np.ndarray
        新規ボーカルの F0 カーブ (Hz)。0 は無声フレーム。

    Returns
    -------
    float
        推定キーシフト（セミトーン）。正 = リファレンスの方が高い（新規を上げる方向）。
    """
    ref_voiced = ref_f0[ref_f0 > 0]
    new_voiced = new_f0[new_f0 > 0]

    if len(ref_voiced) == 0 or len(new_voiced) == 0:
        return 0.0

    ref_median = float(np.median(ref_voiced))
    new_median = float(np.median(new_voiced))

    semitones = 12.0 * np.log2(ref_median / new_median)
    return float(round(semitones))
