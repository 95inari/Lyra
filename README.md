# Lyra

**ボーカルエディット自動化ツール** — 別テイクや別シンガーのボーカルを、リファレンスのピッチ・タイミングに自動で合わせます。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)

---

## 概要

Lyra は、あるボーカル録音を別の録音（リファレンス）に合わせるための処理を自動化するツールです。
DTW によるタイミング補正と RMVPE によるピッチ補正を組み合わせ、手動エディットの工数を大幅に削減します。

**主な用途:**

- 同一曲を別シンガーが歌ったテイクをリファレンスに近づける
- 同一シンガーの複数テイク間でピッチ・タイミングを統一する
- ボーカルミックスの前処理として補正データ（recipe.json）を生成する

## 処理パイプライン

```
入力音声
  │
  ├─ ① ボーカル分離 (Demucs htdemucs)  ※--stem 指定時はスキップ
  ├─ ② F0 推定 (RMVPE)
  ├─ ③ オンセット検出 (librosa)
  ├─ ④ キーシフト推定 / 手動指定
  ├─ ⑤ DTW アライメント
  └─ ⑥ レンダリング (pyrubberband)
         │
         ├─ 補正済み WAV
         └─ recipe.json（補正データ）
```

## 動作環境

| 項目 | 要件 |
|------|------|
| Python | 3.11 以上 |
| OS | macOS / Linux / Windows |
| GPU | 任意（CPU でも動作、ただし処理時間が長くなります） |

## インストール

### 1. リポジトリのクローン

```bash
git clone https://github.com/<owner>/lyra.git
cd lyra
```

### 2. 依存関係のインストール

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .
```

### 3. モデルのダウンロード

```bash
python scripts/download_models.py --rmvpe
```

> RMVPE モデル（約 181 MB）を Hugging Face からダウンロードします。

## 使い方

### CLI

```bash
# 基本的な使用方法
lyra run --ref reference.wav --vocal new_vocal.wav

# 出力ファイルを指定
lyra run --ref reference.wav --vocal new_vocal.wav \
    --out-wav output.wav --out-recipe recipe.json

# プリセットを変更（light / standard / strong）
lyra run --ref reference.wav --vocal new_vocal.wav --preset strong

# ボーカルステムを直接指定（分離処理をスキップ）
lyra run --ref reference.wav --vocal vocal_stem.wav --stem

# キーシフトを手動指定（半音単位）
lyra run --ref reference.wav --vocal new_vocal.wav --key-shift -2
```

#### オプション一覧

| オプション | デフォルト | 説明 |
|-----------|-----------|------|
| `--ref` | 必須 | リファレンス音声ファイル |
| `--vocal` | 必須 | 補正対象のボーカルファイル |
| `--preset` | `standard` | 補正強度 (`light` / `standard` / `strong`) |
| `--stem` | false | ボーカル分離をスキップ |
| `--key-shift` | 自動検出 | キーシフト量（半音単位） |
| `--out-wav` | `output.wav` | 出力 WAV ファイルパス |
| `--out-recipe` | `recipe.json` | 出力 recipe.json パス |

### GUI

```bash
python -m gui.app
```

GUI では以下の操作が可能です:

- ファイルの選択と処理実行
- ピッチカーブの可視化（リファレンス・入力・補正後）
- タイミングワープの可視化
- セグメントごとのピッチ補正量・タイミング補正量の調整
- 補正済み WAV と recipe.json の書き出し

### recipe.json

Lyra は補正データを `recipe.json` として出力します。
このファイルは DAW プラグインや他のツールで読み込んで利用できます。

```json
{
  "version": "0.1",
  "sample_rate": 44100,
  "global_key_shift_semitones": 0.0,
  "segments": [
    {
      "t0": 0.0,
      "t1": 2.5,
      "time_warp_points": [[0.0, 0.0], [1.2, 1.35], [2.5, 2.5]],
      "pitch_target_curve": [[0.0, 220.0], [0.5, 246.9]],
      "confidence": 0.85,
      "pitch_strength": 1.0,
      "time_strength": 1.0
    }
  ]
}
```

## 開発

```bash
# 開発用インストール（テストツール含む）
pip install -e ".[dev]"

# テスト実行（モデル不要）
pytest tests/test_smoke.py -v

# 統合テスト（モデルが必要）
pytest tests/test_integration.py -v

# リント
ruff check .
```

## ライセンスについての注意

Lyra は MIT License で配布されますが、以下の依存ライブラリのライセンスにご注意ください:

- **pyrubberband**: GPL v2+ — この依存関係を含む形での商用クローズドソース利用には制限があります
- **PySide6**: LGPL v3 / 商用ライセンス — 動的リンクにより LGPL 条件下で利用可能
- **RMVPE モデル**: [元リポジトリ](https://github.com/yxlllc/RMVPE) のライセンスを確認してください

## コントリビュート

バグ報告・機能提案・プルリクエストを歓迎します。
詳細は [CONTRIBUTING.md](CONTRIBUTING.md) をご覧ください。

## ライセンス

[MIT License](LICENSE) © 2025 Lyra Contributors