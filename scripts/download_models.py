"""
scripts/download_models.py — モデルファイルのダウンロード

使い方:
  python scripts/download_models.py          # 全モデル
  python scripts/download_models.py --rmvpe  # RMVPE のみ
"""

from __future__ import annotations

import argparse
import sys
import urllib.request
from pathlib import Path

MODELS_DIR = Path(__file__).parent.parent / "models"

MODELS = {
    "rmvpe": {
        "url": "https://huggingface.co/lj1995/VoiceConversionWebUI/resolve/main/rmvpe.pt",
        "dest": MODELS_DIR / "rmvpe.pt",
        "size_mb": 181,
    },
}


def _progress_hook(desc: str):
    def hook(count, block_size, total_size):
        if total_size > 0:
            pct = min(count * block_size / total_size * 100, 100)
            bar = "#" * int(pct / 2)
            print(f"\r  {desc}: [{bar:<50}] {pct:.1f}%", end="", flush=True)
    return hook


def download(name: str, force: bool = False) -> None:
    info = MODELS[name]
    dest: Path = info["dest"]
    dest.parent.mkdir(parents=True, exist_ok=True)

    if dest.exists() and not force:
        print(f"  {name}: スキップ（既存: {dest}）")
        return

    print(f"  {name}: ダウンロード中 (~{info['size_mb']}MB)")
    print(f"    URL: {info['url']}")
    try:
        urllib.request.urlretrieve(info["url"], dest, _progress_hook(name))
        print()  # 改行
        print(f"    → {dest}")
    except Exception as e:
        print(f"\n  ERROR: {e}")
        if dest.exists():
            dest.unlink()
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="lyra モデルダウンロード")
    parser.add_argument("--rmvpe", action="store_true", help="RMVPE のみダウンロード")
    parser.add_argument("--force", action="store_true", help="既存ファイルを上書き")
    args = parser.parse_args()

    targets = ["rmvpe"] if args.rmvpe else list(MODELS.keys())

    print("=" * 50)
    print("  lyra — モデルダウンロード")
    print("=" * 50)

    for name in targets:
        download(name, force=args.force)

    print("\n完了")


if __name__ == "__main__":
    main()
