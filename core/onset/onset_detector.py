"""
onset/onset_detector.py — librosa による発声オンセット検出
"""

from __future__ import annotations

import numpy as np
import librosa


def detect_onsets(
    audio: np.ndarray,
    sr: int,
    hop_length: int = 512,
) -> np.ndarray:
    """
    librosa で発声オンセット時刻を検出する。

    Parameters
    ----------
    audio : np.ndarray
        モノラル音声 (samples,)
    sr : int
        サンプルレート
    hop_length : int
        ホップ長（サンプル数）

    Returns
    -------
    onset_times : np.ndarray
        オンセット時刻（秒）
    """
    onset_frames = librosa.onset.onset_detect(
        y=audio,
        sr=sr,
        hop_length=hop_length,
        backtrack=True,   # オンセットを発声立ち上がり直前に補正
        units="frames",
    )
    onset_times = librosa.frames_to_time(onset_frames, sr=sr, hop_length=hop_length)
    return onset_times.astype(np.float32)
