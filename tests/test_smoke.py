"""
tests/test_smoke.py — 外部モデルを使わない単体スモークテスト

pip install pytest でそのまま実行できる。
"""

import numpy as np
import pytest


SR = 44100
DURATION = 3.0  # 秒


def _sine(freq: float = 440.0, sr: int = SR, duration: float = DURATION) -> np.ndarray:
    """テスト用サイン波を生成する。"""
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    return (np.sin(2 * np.pi * freq * t) * 0.5).astype(np.float32)


# ---- audio_io --------------------------------------------------------------

def test_audio_io_save_load(tmp_path):
    from core.audio_io import load, save

    audio = _sine()
    path = tmp_path / "test.wav"
    save(str(path), audio, SR)

    loaded, sr = load(str(path), target_sr=SR)
    assert sr == SR
    assert loaded.shape == audio.shape
    assert np.allclose(audio, loaded, atol=1e-3)


def test_audio_io_resample(tmp_path):
    from core.audio_io import load, save

    audio = _sine()
    path = tmp_path / "test.wav"
    save(str(path), audio, SR)

    loaded, sr = load(str(path), target_sr=22050)
    assert sr == 22050
    assert loaded.shape[0] == pytest.approx(22050 * DURATION, abs=10)


# ---- key_detector ----------------------------------------------------------

def test_key_detector_unison():
    from core.key_detector import detect_key_shift

    f0 = np.array([440.0, 440.0, 0.0, 440.0], dtype=np.float32)
    shift = detect_key_shift(f0, f0)
    assert shift == 0.0


def test_key_detector_octave():
    from core.key_detector import detect_key_shift

    ref_f0 = np.array([440.0, 440.0, 440.0], dtype=np.float32)
    new_f0 = ref_f0 * 0.5  # 1オクターブ下
    shift = detect_key_shift(ref_f0, new_f0)
    assert shift == 12.0


def test_key_detector_silence():
    from core.key_detector import detect_key_shift

    f0 = np.zeros(100, dtype=np.float32)
    shift = detect_key_shift(f0, f0)
    assert shift == 0.0


# ---- recipe/schema ---------------------------------------------------------

def test_recipe_roundtrip(tmp_path):
    from core.recipe.schema import Recipe, Segment, Warning

    seg = Segment(
        t0=0.0, t1=2.0,
        time_warp_points=[(0.0, 0.0), (2.0, 2.0)],
        pitch_target_curve=[(0.0, 440.0), (1.0, 480.0)],
        confidence=0.85,
        pitch_strength=0.85,
        time_strength=0.85,
        protect_unvoiced=True,
    )
    warn = Warning(t0=1.0, t1=1.5, reason="low_confidence", detail="test")
    recipe = Recipe(
        version="0.1",
        sample_rate=44100,
        global_key_shift_semitones=-1.0,
        segments=[seg],
        warnings=[warn],
    )

    path = tmp_path / "recipe.json"
    recipe.save(str(path))

    loaded = Recipe.load(str(path))
    assert loaded.version == "0.1"
    assert loaded.global_key_shift_semitones == -1.0
    assert len(loaded.segments) == 1
    assert loaded.segments[0].confidence == 0.85
    assert len(loaded.warnings) == 1
    assert loaded.warnings[0].reason == "low_confidence"


# ---- recipe/generator ------------------------------------------------------

def test_generator_basic():
    from core.recipe.generator import generate

    duration = 4.0
    n_frames = 400
    times = np.linspace(0, duration, n_frames, endpoint=False, dtype=np.float32)
    f0 = np.full(n_frames, 440.0, dtype=np.float32)
    voiced = np.ones(n_frames, dtype=bool)

    # ダミーアライメント（等倍）
    warp_map = [(float(t), float(t)) for t in times[::10]]
    confidence = np.ones(n_frames, dtype=np.float32)

    recipe = generate(
        new_audio_duration=duration,
        sample_rate=SR,
        global_key_shift_semitones=0.0,
        alignment={"warp_map": warp_map, "confidence_per_frame": confidence, "new_times": times},
        ref_f0=f0, ref_times=times,
        new_f0=f0, new_times=times,
        voiced_mask=voiced,
    )

    assert len(recipe.segments) > 0
    assert recipe.sample_rate == SR
    for seg in recipe.segments:
        assert 0.0 <= seg.confidence <= 1.0
        assert 0.0 <= seg.pitch_strength <= 1.0


# ---- voiced_detector -------------------------------------------------------

def test_voiced_detector_silence():
    from core.onset.voiced_detector import detect_voiced

    silence = np.zeros(SR, dtype=np.float32)
    mask = detect_voiced(silence, SR)
    assert not mask.any()


def test_voiced_detector_sine():
    from core.onset.voiced_detector import detect_voiced

    audio = _sine(440.0)
    mask = detect_voiced(audio, SR)
    assert mask.mean() > 0.5  # 大半のフレームが有声と判定されること
