"""
audio_io.py — WAV/AIFF の読み書きとサンプルレート正規化
"""

from pathlib import Path
import numpy as np
import soundfile as sf
import torch
import torchaudio

SUPPORTED_EXTENSIONS = {".wav", ".aiff", ".aif", ".flac"}


def load(
    path: str | Path,
    target_sr: int | None = None,
    mono: bool = True,
) -> tuple[np.ndarray, int]:
    """
    音声ファイルを読み込む。

    Returns
    -------
    audio : np.ndarray
        mono=True のとき shape (samples,)、False のとき (channels, samples)
    sr : int
        サンプルレート
    """
    path = Path(path)
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"非対応フォーマット: {path.suffix}。対応: {SUPPORTED_EXTENSIONS}"
        )

    audio, sr = sf.read(str(path), always_2d=True)  # (samples, channels)
    audio = audio.T.astype(np.float32)               # (channels, samples)

    if mono and audio.shape[0] > 1:
        audio = audio.mean(axis=0, keepdims=True)    # (1, samples)

    if target_sr is not None and sr != target_sr:
        tensor = torch.from_numpy(audio)
        tensor = torchaudio.functional.resample(tensor, sr, target_sr)
        audio = tensor.numpy()
        sr = target_sr

    return (audio[0], sr) if mono else (audio, sr)


def save(
    path: str | Path,
    audio: np.ndarray,
    sr: int,
    subtype: str = "PCM_24",
) -> None:
    """
    音声を WAV ファイルに書き出す。

    Parameters
    ----------
    audio : np.ndarray
        shape (samples,) または (channels, samples)
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    data = audio.T if audio.ndim == 2 else audio  # soundfile は (samples, channels)
    sf.write(str(path), data, sr, subtype=subtype)
