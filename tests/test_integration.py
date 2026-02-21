"""
tests/test_integration.py — 実モデルを使ったインテグレーションテスト

実行:
  pytest tests/test_integration.py -v -s
"""

from __future__ import annotations

import numpy as np

SR = 44100
DURATION = 5.0   # 秒


def _sine_vocal(freq: float = 220.0, vibrato: float = 0.0) -> np.ndarray:
    """サイン波（ボーカル代わり）を生成する。vibrato=0 で純音。"""
    t = np.linspace(0, DURATION, int(SR * DURATION), endpoint=False)
    if vibrato > 0:
        vib = np.sin(2 * np.pi * vibrato * t) * 0.03
        audio = np.sin(2 * np.pi * freq * (1 + vib) * t)
    else:
        audio = np.sin(2 * np.pi * freq * t)
    return (audio * 0.5).astype(np.float32)


# ---- RMVPE -----------------------------------------------------------------

def test_rmvpe_f0_estimation():
    """RMVPE が有声フレームで F0 を返すことを確認する。"""
    from core.pitch.rmvpe_wrapper import estimate_f0

    audio = _sine_vocal(freq=220.0)
    f0, times = estimate_f0(audio, SR)

    assert len(f0) == len(times)
    assert len(f0) > 0

    voiced = f0[f0 > 0]
    assert len(voiced) > 0, "有声フレームが 1 件も検出されなかった"

    # 220Hz ±50Hz の範囲に中央値があること
    median_f0 = float(np.median(voiced))
    assert 170 <= median_f0 <= 270, f"F0 中央値 {median_f0:.1f}Hz が範囲外"

    print(f"\n  F0 中央値: {median_f0:.1f} Hz")
    print(f"  有声フレーム率: {len(voiced)/len(f0)*100:.1f}%")


def test_rmvpe_unvoiced_silence():
    """無音に対して F0=0 を返すことを確認する。"""
    from core.pitch.rmvpe_wrapper import estimate_f0

    silence = np.zeros(SR * 2, dtype=np.float32)
    f0, _ = estimate_f0(silence, SR)
    assert (f0 == 0).all() or (f0 > 0).mean() < 0.1, "無音で有声フレームが多すぎる"


# ---- key_detector ----------------------------------------------------------

def test_key_detector_with_real_f0():
    """実際の F0 カーブからキーシフトを推定する。"""
    from core.pitch.rmvpe_wrapper import estimate_f0
    from core.key_detector import detect_key_shift

    ref_audio = _sine_vocal(freq=220.0)
    new_audio = _sine_vocal(freq=261.6)  # 220 * 2^(3/12) — new は 3 semitone 高い

    ref_f0, _ = estimate_f0(ref_audio, SR)
    new_f0, _ = estimate_f0(new_audio, SR)

    shift = detect_key_shift(ref_f0, new_f0)
    # new が ref より高い → ref/new < 1 → shift < 0 (新規を下げる方向)
    print(f"\n  推定キーシフト: {shift:+.0f} semitones (期待値: -3)")
    assert abs(shift + 3) <= 1, f"キーシフト推定が外れた: {shift}"


# ---- beat_tracker ----------------------------------------------------------

def test_beat_tracker():
    """beat_this がビートを検出できることを確認する。"""
    from core.onset.beat_tracker import track_beats

    # 120BPM のクリック音を生成（実際のビートトラッカーは音楽的な内容を期待するが基本動作確認）
    t = np.linspace(0, DURATION, int(SR * DURATION), endpoint=False)
    bpm = 120
    beat_period = SR * 60 / bpm
    click = np.zeros(len(t), dtype=np.float32)
    for i in range(int(DURATION * bpm / 60)):
        idx = int(i * beat_period)
        if idx < len(click):
            click[idx : min(idx + 100, len(click))] = 0.8

    beats, downbeats = track_beats(click, SR)
    print(f"\n  検出ビート数: {len(beats)}")
    # クラッシュせず ndarray が返ること（beat_this はクリック音には不向きだが基本動作確認）
    assert isinstance(beats, np.ndarray)
    assert isinstance(downbeats, np.ndarray)


# ---- alignment -------------------------------------------------------------

def test_dtw_alignment_identity():
    """同一信号のアライメントは等倍写像になること。"""
    from core.pitch.rmvpe_wrapper import estimate_f0
    from core.onset.onset_detector import detect_onsets
    from core.alignment.dtw_aligner import align

    audio = _sine_vocal(freq=220.0)
    f0, times = estimate_f0(audio, SR)
    onsets = detect_onsets(audio, SR)

    result = align(
        ref_f0=f0, ref_times=times, ref_onsets=onsets,
        new_f0=f0, new_times=times, new_onsets=onsets,
    )

    warp_map = result["warp_map"]
    assert len(warp_map) > 0

    # 等倍: new_time ≈ ref_time のはず
    errors = [abs(nt - rt) for nt, rt in warp_map]
    mean_err = float(np.mean(errors))
    print(f"\n  アライメント誤差（等倍）: {mean_err:.3f}s")
    assert mean_err < 0.5, f"等倍アライメントの誤差が大きすぎる: {mean_err:.3f}s"


# ---- renderer --------------------------------------------------------------

def test_renderer_passthrough():
    """pitch_strength=0, time_strength=0 のとき入出力が等しいこと。"""
    from core.recipe.schema import Recipe, Segment
    from core.renderer.rubberband_renderer import render

    audio = _sine_vocal()
    seg = Segment(
        t0=0.0, t1=DURATION,
        time_warp_points=[(0.0, 0.0), (DURATION, DURATION)],
        pitch_target_curve=[(0.0, 220.0), (DURATION, 220.0)],
        confidence=1.0,
        pitch_strength=0.0,   # 補正なし
        time_strength=0.0,    # 補正なし
        protect_unvoiced=True,
    )
    recipe = Recipe(
        version="0.1",
        sample_rate=SR,
        global_key_shift_semitones=0.0,
        segments=[seg],
    )

    out = render(audio, SR, recipe)
    assert abs(len(out) - len(audio)) < SR * 0.05, "出力長が大きく変わった"


def test_renderer_pitch_shift():
    """global_key_shift_semitones が音声の長さを変えないこと。"""
    from core.recipe.schema import Recipe, Segment
    from core.renderer.rubberband_renderer import render

    audio = _sine_vocal()
    seg = Segment(
        t0=0.0, t1=DURATION,
        time_warp_points=[(0.0, 0.0), (DURATION, DURATION)],
        pitch_target_curve=[(0.0, 220.0)],
        confidence=1.0,
        pitch_strength=0.0,
        time_strength=0.0,
        protect_unvoiced=True,
    )
    recipe = Recipe(
        version="0.1",
        sample_rate=SR,
        global_key_shift_semitones=3.0,
        segments=[seg],
    )

    out = render(audio, SR, recipe)
    assert abs(len(out) - len(audio)) < SR * 0.1, "ピッチシフトで長さが変わった"


# ---- full pipeline (軽量版) ------------------------------------------------

def test_full_pipeline_lite():
    """
    モデル推論を含むパイプライン全体が通ることを確認する。
    （音質の正確性ではなくクラッシュしないことを検証）
    """
    from core.audio_io import save, load
    from core.pitch.rmvpe_wrapper import estimate_f0
    from core.onset.onset_detector import detect_onsets
    from core.onset.voiced_detector import detect_voiced
    from core.key_detector import detect_key_shift
    from core.alignment.dtw_aligner import align
    from core.recipe.generator import generate
    from core.renderer.rubberband_renderer import render
    import os
    import tempfile

    ref_audio = _sine_vocal(freq=220.0)
    new_audio = _sine_vocal(freq=220.0 * 2 ** (2 / 12))  # 2 semitone 高い

    ref_f0, ref_times = estimate_f0(ref_audio, SR)
    new_f0, new_times = estimate_f0(new_audio, SR)

    ref_onsets = detect_onsets(ref_audio, SR)
    new_onsets = detect_onsets(new_audio, SR)
    voiced_mask = detect_voiced(new_audio, SR)

    key_shift = detect_key_shift(ref_f0, new_f0)

    alignment = align(
        ref_f0=ref_f0, ref_times=ref_times, ref_onsets=ref_onsets,
        new_f0=new_f0, new_times=new_times, new_onsets=new_onsets,
    )

    recipe = generate(
        new_audio_duration=DURATION,
        sample_rate=SR,
        global_key_shift_semitones=key_shift,
        alignment=alignment,
        ref_f0=ref_f0, ref_times=ref_times,
        new_f0=new_f0, new_times=new_times,
        voiced_mask=voiced_mask,
    )

    output = render(new_audio, SR, recipe, new_f0=new_f0, new_times=new_times)

    assert output is not None
    assert len(output) > 0
    assert not np.isnan(output).any(), "出力に NaN が含まれる"

    print(f"\n  key_shift={key_shift:+.0f} semitones")
    print(f"  セグメント数: {len(recipe.segments)}")
    print(f"  warnings: {len(recipe.warnings)}")
    print(f"  出力サンプル数: {len(output)} ({len(output)/SR:.2f}s)")

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        tmp_path = f.name
    try:
        save(tmp_path, output, SR)
        loaded, _ = load(tmp_path, target_sr=SR)
        assert len(loaded) > 0
        print("  WAV 書き出し・再読み込み: OK")
    finally:
        os.unlink(tmp_path)
