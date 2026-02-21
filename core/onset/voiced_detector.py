"""
onset/voiced_detector.py — 有声/無声区間の検出

ゼロ交差率 + RMS エネルギーのルールベースで判定する（Phase 0 MVP）。
精度が足りない場合は webrtcvad に差し替える（pip install webrtcvad）。
"""

from __future__ import annotations

import numpy as np
import librosa


def detect_voiced(
    audio: np.ndarray,
    sr: int,
    hop_length: int = 512,
    zcr_threshold: float = 0.15,
    rms_threshold: float = 0.02,
) -> np.ndarray:
    """
    有声フレームを検出する。

    子音・ブレスなどの無声区間は ZCR が高く RMS が低い特性を使って判定する。

    Parameters
    ----------
    audio : np.ndarray
        モノラル音声 (samples,)
    sr : int
        サンプルレート
    hop_length : int
        ホップ長
    zcr_threshold : float
        これ以上のゼロ交差率を「無声（子音・ノイズ）」と判定
    rms_threshold : float
        これ以下の正規化 RMS を「無音・ブレス」と判定

    Returns
    -------
    voiced_mask : np.ndarray
        bool 配列 (frames,)。True = 有声、False = 無声/無音
    """
    zcr = librosa.feature.zero_crossing_rate(audio, hop_length=hop_length)[0]
    rms = librosa.feature.rms(y=audio, hop_length=hop_length)[0]

    rms_norm = rms / (rms.max() + 1e-8)

    voiced = (zcr < zcr_threshold) & (rms_norm > rms_threshold)
    return voiced
