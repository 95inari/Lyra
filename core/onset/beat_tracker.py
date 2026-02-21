"""
onset/beat_tracker.py — beat_this によるニューラルビート追跡

依存: pip install beat-this
"""

from __future__ import annotations

import numpy as np

# モデルキャッシュ: device → Audio2Beats インスタンス
_predictor_cache: dict[str, object] = {}


def _get_predictor(device: str) -> object:
    """キャッシュ済み Audio2Beats を返す。なければロードしてキャッシュする。"""
    if device not in _predictor_cache:
        from beat_this.inference import Audio2Beats
        _predictor_cache[device] = Audio2Beats(
            checkpoint_path="final0", device=device, dbn=False
        )
    return _predictor_cache[device]


def track_beats(audio: np.ndarray, sr: int) -> tuple[np.ndarray, np.ndarray]:
    """
    beat_this でビート・ダウンビート時刻を検出する。

    Parameters
    ----------
    audio : np.ndarray
        モノラル音声 (samples,)
    sr : int
        サンプルレート

    Returns
    -------
    beat_times : np.ndarray
        ビート時刻（秒）
    downbeat_times : np.ndarray
        ダウンビート時刻（秒）
    """
    import torch
    device = "cuda" if torch.cuda.is_available() else "cpu"
    predictor = _get_predictor(device)
    beat_times, downbeat_times = predictor(audio, sr)

    return np.array(beat_times, dtype=np.float32), np.array(downbeat_times, dtype=np.float32)
