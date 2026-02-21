"""
cli/main.py — lyra コマンドラインインターフェース

使い方:
  lyra run --ref reference.wav --vocal new_vocal.wav
  lyra run --ref reference.wav --vocal new_vocal.wav --stem --preset light
  lyra run --ref reference.wav --vocal new_vocal.wav --key-shift -2
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path


# ---- プリセット定義 -------------------------------------------------------
PRESETS = {
    "light": {
        "description": "軽め — 自然な仕上がりを優先",
        "confidence_low": 0.6,
        "confidence_high": 0.9,
        "band_radius": 0.08,
    },
    "standard": {
        "description": "標準 — バランス重視",
        "confidence_low": 0.5,
        "confidence_high": 0.8,
        "band_radius": 0.10,
    },
    "strong": {
        "description": "強め — リファレンスへの追従を最大化",
        "confidence_low": 0.4,
        "confidence_high": 0.7,
        "band_radius": 0.12,
    },
}


# ---- CLI 定義 -------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lyra",
        description="lyra — ボーカルエディット自動化ツール",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
例:
  lyra run --ref mix.wav --vocal vocal.wav
  lyra run --ref stem.wav --vocal vocal.wav --stem
  lyra run --ref mix.wav --vocal vocal.wav --preset strong --key-shift -2
        """,
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # run サブコマンド
    run = sub.add_parser("run", help="ボーカル補正を実行する")
    run.add_argument("--ref", required=True, metavar="FILE",
                     help="リファレンス音源（2mix または Vocal Stem）")
    run.add_argument("--vocal", required=True, metavar="FILE",
                     help="新規ドライボーカル")
    run.add_argument("--out-wav", default="edited_vocal.wav", metavar="FILE",
                     help="出力 WAV パス（デフォルト: edited_vocal.wav）")
    run.add_argument("--out-recipe", default="recipe.json", metavar="FILE",
                     help="出力 recipe.json パス（デフォルト: recipe.json）")
    run.add_argument("--stem", action="store_true",
                     help="リファレンスを Vocal Stem として扱う（分離をスキップ）")
    run.add_argument("--preset", choices=list(PRESETS.keys()), default="standard",
                     help="補正強度プリセット（デフォルト: standard）")
    run.add_argument("--key-shift", type=float, default=None, metavar="SEMITONES",
                     help="キーシフト量（セミトーン）。省略時は自動推定")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "run":
        _cmd_run(args)


# ---- run コマンド実装 -------------------------------------------------------

def _cmd_run(args: argparse.Namespace) -> None:
    from core.audio_io import load, save
    from core.separation.demucs_wrapper import separate_vocal
    from core.pitch.rmvpe_wrapper import estimate_f0
    from core.onset.onset_detector import detect_onsets
    from core.onset.voiced_detector import detect_voiced
    from core.key_detector import detect_key_shift
    from core.alignment.dtw_aligner import align
    from core.recipe.generator import generate
    from core.renderer.rubberband_renderer import render

    preset = PRESETS[args.preset]
    TARGET_SR = 44100
    out_files = [Path(args.out_wav), Path(args.out_recipe)]

    _print_header(args, preset)

    total_start = time.perf_counter()

    try:
        # --- Step 1: 読み込み ---
        _step(1, 7, "読み込み中")
        ref_audio, _ = load(args.ref, target_sr=TARGET_SR)
        new_audio, _ = load(args.vocal, target_sr=TARGET_SR)
        ref_dur = len(ref_audio) / TARGET_SR
        new_dur = len(new_audio) / TARGET_SR
        _info(f"リファレンス: {ref_dur:.1f}s  新規ボーカル: {new_dur:.1f}s")

        # --- Step 2: ボーカル分離 ---
        if args.stem:
            _step(2, 7, "Stem 入力 — 分離をスキップ")
            ref_vocal = ref_audio
        else:
            _step(2, 7, "ボーカル分離中 (Demucs htdemucs)")
            ref_vocal = separate_vocal(ref_audio, TARGET_SR)

        # --- Step 3: F0 解析 ---
        _step(3, 7, "F0 解析中 (RMVPE)")
        ref_f0, ref_times = estimate_f0(ref_vocal, TARGET_SR)
        new_f0, new_times = estimate_f0(new_audio, TARGET_SR)
        _info(
            f"有声フレーム — ref: {(ref_f0 > 0).sum()}  new: {(new_f0 > 0).sum()}"
        )

        # --- Step 4: オンセット・有声区間検出 ---
        _step(4, 7, "オンセット・有声区間検出中")
        ref_onsets = detect_onsets(ref_vocal, TARGET_SR)
        new_onsets = detect_onsets(new_audio, TARGET_SR)
        voiced_mask = detect_voiced(new_audio, TARGET_SR)
        _info(f"オンセット — ref: {len(ref_onsets)}点  new: {len(new_onsets)}点")

        # --- Step 5: キーシフト推定 ---
        _step(5, 7, "キーシフト推定中")
        if args.key_shift is not None:
            key_shift = float(args.key_shift)
            _info(f"手動指定: {key_shift:+.1f} semitones")
        else:
            key_shift = detect_key_shift(ref_f0, new_f0)
            _info(f"自動推定: {key_shift:+.1f} semitones")

        # --- Step 6: アライメント ---
        _step(6, 7, "DTW アライメント中")
        alignment = align(
            ref_f0=ref_f0, ref_times=ref_times, ref_onsets=ref_onsets,
            new_f0=new_f0, new_times=new_times, new_onsets=new_onsets,
            band_radius=preset["band_radius"],
        )

        # --- Step 7: レンダリング ---
        _step(7, 7, "レシピ生成・レンダリング中")

        recipe = generate(
            new_audio_duration=len(new_audio) / TARGET_SR,
            sample_rate=TARGET_SR,
            global_key_shift_semitones=key_shift,
            alignment=alignment,
            ref_f0=ref_f0, ref_times=ref_times,
            new_f0=new_f0, new_times=new_times,
            voiced_mask=voiced_mask,
            confidence_low=preset["confidence_low"],
            confidence_high=preset["confidence_high"],
        )

        recipe.save(args.out_recipe)
        _info(f"recipe.json → {args.out_recipe}")

        n_warn = len(recipe.warnings)
        if n_warn:
            _warn(f"低信頼区間: {n_warn} セグメント（warnings に記録済み）")

        output = render(new_audio, TARGET_SR, recipe, new_f0=new_f0, new_times=new_times)
        save(args.out_wav, output, TARGET_SR)
        _info(f"WAV → {args.out_wav}")

        elapsed = time.perf_counter() - total_start
        print(f"\n完了 ({elapsed:.1f}s)")

    except Exception as e:
        print(f"\n[エラー] {type(e).__name__}: {e}", file=sys.stderr)
        # 不完全な出力ファイルを削除してクリーンな状態に戻す
        for f in out_files:
            f.unlink(missing_ok=True)
        sys.exit(1)


# ---- 表示ヘルパー -----------------------------------------------------------

def _print_header(args: argparse.Namespace, preset: dict) -> None:
    print("=" * 56)
    print("  lyra — ボーカルエディット自動化ツール")
    print("=" * 56)
    print(f"  ref    : {args.ref}")
    print(f"  vocal  : {args.vocal}")
    print(f"  preset : {args.preset} — {preset['description']}")
    print(f"  stem   : {'yes' if args.stem else 'no'}")
    print("=" * 56)


def _step(n: int, total: int, msg: str) -> None:
    print(f"\n[{n}/{total}] {msg}...")


def _info(msg: str) -> None:
    print(f"       {msg}")


def _warn(msg: str) -> None:
    print(f"  [!]  {msg}")


if __name__ == "__main__":
    main()
