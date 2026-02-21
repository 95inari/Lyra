# Changelog

このプロジェクトの変更履歴です。[Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) 形式に従い、
[Semantic Versioning](https://semver.org/lang/ja/) を採用しています。

## [Unreleased]

### Known Issues
- グローバル状態の競合（並列実行時のレースコンディション）
- `protect_unvoiced` フラグが renderer に未適用
- GUI がファイルダイアログで MP3 を許可するが、処理は非対応

## [0.1.0] - 2025-XX-XX

### Added
- CLI コマンド `lyra run` による基本処理パイプライン
- Demucs htdemucs を使ったボーカル分離
- RMVPE による F0（基本周波数）推定
- torchcrepe によるバックアップ F0 推定
- DTW（動的時間伸縮法）によるタイミングアライメント
- pyrubberband によるピッチ補正・タイミング補正レンダリング
- `recipe.json` フォーマットによる補正データの出力
- プリセット機能（`light` / `standard` / `strong`）
- キーシフト自動検出・手動指定オプション
- PySide6 製 GUI（ピッチビュー・ワープビュー・セグメントパネル）
- モデルダウンロードスクリプト (`scripts/download_models.py`)

[Unreleased]: https://github.com/<owner>/lyra/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/<owner>/lyra/releases/tag/v0.1.0
