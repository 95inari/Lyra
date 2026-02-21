"""
pitch/torchcrepe_wrapper.py — torchcrepe による F0 推定（バックアップ）

RMVPE が合わないケースで使用する。
依存: pip install torchcrepe
"""

from __future__ import annotations

import numpy as np
import torch
import torchaudio

CREPE_SR = 16000
HOP_LENGTH = 160


def estimate_f0(
    audio: np.ndarray,
    sr: int,
    fmin: float = 50.0,
    fmax: float = 1100.0,
    model_capacity: str = "full",
) -> tuple[np.ndarray, np.ndarray]:
    """
    torchcrepe で F0 カーブを推定する。

    Parameters
    ----------
    audio : np.ndarray
        モノラル音声 (samples,)
    sr : int
        入力サンプルレート
    fmin, fmax : float
        推定 F0 の範囲（Hz）
    model_capacity : str
        "tiny" | "small" | "medium" | "large" | "full"

    Returns
    -------
    f0 : np.ndarray
        F0 カーブ (Hz)、shape (frames,)。無声フレームは 0.0。
    times : np.ndarray
        各フレームの時刻（秒）
    """
    import torchcrepe

    device = "cuda" if torch.cuda.is_available() else "cpu"

    if sr != CREPE_SR:
        tensor = torch.from_numpy(audio).float().unsqueeze(0)
        tensor = torchaudio.functional.resample(tensor, sr, CREPE_SR)
        audio_tensor = tensor
    else:
        audio_tensor = torch.from_numpy(audio).float().unsqueeze(0)

    audio_tensor = audio_tensor.to(device)

    frequency, confidence = torchcrepe.predict(
        audio_tensor,
        CREPE_SR,
        hop_length=HOP_LENGTH,
        fmin=fmin,
        fmax=fmax,
        model=model_capacity,
        return_periodicity=True,
        device=device,
    )

    # 有声判定: メディアンフィルタ後の periodicity > 0.1
    voiced = torchcrepe.filter.median(confidence, 3) > 0.1

    f0 = frequency.squeeze(0).cpu().numpy().astype(np.float32)
    voiced_mask = voiced.squeeze(0).cpu().numpy()
    f0[~voiced_mask] = 0.0

    frame_period = HOP_LENGTH / CREPE_SR
    times = np.arange(len(f0), dtype=np.float32) * frame_period

    return f0, times
