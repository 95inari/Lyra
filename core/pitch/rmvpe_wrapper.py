"""
pitch/rmvpe_wrapper.py — RMVPE による F0 推定（第一候補）

ソース: yxlllc/RMVPE (core/pitch/rmvpe_src/ にベンダリング)
モデル: models/rmvpe.pt — scripts/download_models.py で取得
"""

from __future__ import annotations

import sys
from pathlib import Path
import numpy as np
import torch

# ベンダリングした RMVPE ソースへのパス（モジュールロード時に一度だけ設定）
_SRC_DIR = Path(__file__).parent / "rmvpe_src"
_DEFAULT_MODEL_PATH = Path(__file__).parents[2] / "models" / "rmvpe.pt"

if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

HOP_LENGTH = 160   # 16kHz で 10ms/frame
RMVPE_SR = 16000

# モデルキャッシュ: (model_path_str, device) → RMVPE インスタンス
_model_cache: dict[tuple[str, str], object] = {}


def _get_model(path: Path, device: str) -> object:
    """キャッシュ済みモデルを返す。なければロードしてキャッシュする。"""
    key = (str(path), device)
    if key not in _model_cache:
        from src.inference import RMVPE
        _model_cache[key] = RMVPE(model_path=str(path), hop_length=HOP_LENGTH)
    return _model_cache[key]


def estimate_f0(
    audio: np.ndarray,
    sr: int,
    threshold: float = 0.03,
    model_path: str | Path | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """
    RMVPE で F0 カーブを推定する。

    Parameters
    ----------
    audio : np.ndarray
        モノラル音声 (samples,) — サンプルレートは任意
    sr : int
        入力サンプルレート（RMVPE 内部で 16kHz にリサンプル）
    threshold : float
        有声判定の閾値
    model_path : str | Path | None
        モデルファイルのパス。None の場合は models/rmvpe.pt を使用。

    Returns
    -------
    f0 : np.ndarray
        F0 カーブ (Hz)、shape (frames,)。無声フレームは 0.0。
    times : np.ndarray
        各フレームの時刻（秒）、shape (frames,)。
    """
    path = Path(model_path) if model_path else _DEFAULT_MODEL_PATH
    if not path.exists():
        raise FileNotFoundError(
            f"RMVPE モデルが見つかりません: {path}\n"
            "  → python scripts/download_models.py を実行してください"
        )

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = _get_model(path, device)

    audio_f32 = audio.astype(np.float32)
    f0 = model.infer_from_audio(audio_f32, sample_rate=sr, device=device, thred=threshold)
    # f0 shape: (frames,), Hz, 0 = unvoiced

    frame_period = HOP_LENGTH / RMVPE_SR  # 秒/フレーム
    times = np.arange(len(f0), dtype=np.float32) * frame_period

    return f0.astype(np.float32), times
