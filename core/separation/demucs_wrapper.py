"""
separation/demucs_wrapper.py — Demucs v4 (htdemucs) によるボーカル分離
"""

import numpy as np
import torch
import torchaudio

DEMUCS_SR = 44100

# モデルキャッシュ: (model_name, device) → モデルインスタンス
_model_cache: dict[tuple[str, str], object] = {}


def _get_model(model_name: str, device: str) -> object:
    """キャッシュ済み Demucs モデルを返す。なければロードしてキャッシュする。"""
    key = (model_name, device)
    if key not in _model_cache:
        from demucs.pretrained import get_model
        model = get_model(model_name)
        model.to(device)
        model.eval()
        _model_cache[key] = model
    return _model_cache[key]


def separate_vocal(
    audio: np.ndarray,
    sr: int,
    model_name: str = "htdemucs",
) -> np.ndarray:
    """
    Demucs で 2mix からボーカルを抽出する。

    Parameters
    ----------
    audio : np.ndarray
        shape (samples,) または (2, samples)
    sr : int
        入力サンプルレート
    model_name : str
        使用する Demucs モデル名

    Returns
    -------
    np.ndarray
        モノラルボーカル (samples,) at 44100 Hz
    """
    from demucs.apply import apply_model

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = _get_model(model_name, device)

    # (channels, samples) に正規化
    tensor = torch.from_numpy(audio).float()
    if tensor.ndim == 1:
        tensor = tensor.unsqueeze(0)  # (1, samples)

    # 44100 Hz にリサンプル
    if sr != DEMUCS_SR:
        tensor = torchaudio.functional.resample(tensor, sr, DEMUCS_SR)

    # ステレオに変換 (Demucs は 2ch を期待)
    if tensor.shape[0] == 1:
        tensor = tensor.repeat(2, 1)

    tensor = tensor.unsqueeze(0).to(device)  # (batch=1, channels=2, samples)

    with torch.no_grad():
        sources = apply_model(model, tensor, device=device)
    # sources: (batch, n_sources, channels, samples)

    vocal_idx = model.sources.index("vocals")
    vocal = sources[0, vocal_idx]          # (2, samples)
    vocal_mono = vocal.mean(dim=0).cpu().numpy()  # (samples,)

    return vocal_mono
