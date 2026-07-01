# Changelog

このプロジェクトの変更履歴です。[Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) 形式に従い、
[Semantic Versioning](https://semver.org/lang/ja/) を採用しています。

## [Unreleased]

### Added
- 多言語 README（英語・中国語・韓国語・スペイン語）

### Fixed
- グローバル状態の競合を解消（`generate()` の confidence 閾値を引数化）
- `sys.path.insert` の重複実行を解消（モジュールロード時に一度だけ実行）
- `protect_unvoiced` フラグを renderer に実装（無声区間へのピッチシフトを無効化）
- GUI ファイルダイアログから未対応の MP3 フィルタを削除

詳細は [PRODUCTION_FIXES.md](PRODUCTION_FIXES.md) を参照してください。

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
