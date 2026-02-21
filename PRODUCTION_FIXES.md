# 本番環境対応 修正計画

> 作成日: 2026-02-21
> 調査結果: `本番環境耐性 調査レポート` に基づく
> **ステータス: 全11項目 対応済み ✅**

---

## 優先度1 — Critical（必須修正）

### Fix-1: グローバル状態の競合除去 ✅

**問題**
`generate()` の呼び出し前にモジュールレベル変数を直接書き換えている。バックグラウンドスレッド（`PipelineWorker`）から呼ばれるため、将来的な並行実行で race condition が発生する。

**対象ファイル**
- `core/recipe/generator.py` — `CONFIDENCE_LOW`, `CONFIDENCE_HIGH` をグローバル変数から関数引数へ
- `cli/main.py:160-161` — 変数書き換え → `generate()` の引数として渡す
- `gui/worker.py:123-124` — 同上

**対応済み**: `generate()` は `confidence_low` / `confidence_high` を引数で受け取る設計になっており、グローバル変数への書き換えは行われていない。

---

### Fix-2: `sys.path.insert` をモジュールレベルに移動 ✅

**問題**
`estimate_f0()` を呼ぶたびに `sys.path.insert(0, ...)` が実行される。スレッドセーフでなく、重複エントリが蓄積される。

**対象ファイル**
- `core/pitch/rmvpe_wrapper.py:49-51`

**対応済み**: `sys.path.insert` はファイル先頭のモジュールレベルで `if str(_SRC_DIR) not in sys.path:` ガード付きで一度だけ実行される。

---

### Fix-3: `protect_unvoiced` をレンダラーで実装 ✅

**問題**
`Segment.protect_unvoiced` は schema で定義・recipe で設定されているが、`rubberband_renderer.py` の `_apply_segment()` では一切チェックされていない。無声区間（子音・ブレス）にもピッチシフトが適用され、音質アーティファクトが発生する。

**対象ファイル**
- `core/renderer/rubberband_renderer.py:104-109`

**対応済み**: `pitch_strength_eff = 0.0 if seg.protect_unvoiced else seg.pitch_strength` が実装済み。

---

## 優先度2 — Moderate（リリース前に対応）

### Fix-4: Beat tracking の無駄な計算を除去 ✅

**問題**
`track_beats()` をリファレンス・新規両方に対して呼び出しているが、返り値は `_` で即座に破棄されており、アライメントにも使われていない。

**対象ファイル**
- `cli/main.py:132-133`
- `gui/worker.py:100-101`

**対応済み**: `track_beats()` の呼び出しは `cli/main.py` にも `gui/worker.py` にも存在しない。

---

### Fix-5: GUI ファイルダイアログの MP3 フィルタを削除 ✅

**問題**
ファイルダイアログに `*.mp3` が含まれているが、`audio_io.py` の `SUPPORTED_EXTENSIONS` には `.mp3` がない。

**対象ファイル**
- `gui/main_window.py:176`

**対応済み**: ファイルダイアログフィルタは `"Audio Files (*.wav *.flac *.aiff *.aif);;All Files (*)"` のみ。

---

### Fix-6: CLI に try/except と部分ファイルの後処理を追加 ✅

**問題**
`_cmd_run()` に例外処理がない。途中失敗時に不完全な出力ファイルが残る。

**対象ファイル**
- `cli/main.py:88-185`

**対応済み**: 全体を `try/except` で囲み、失敗時に `out_files` を `unlink(missing_ok=True)` でクリーンアップしてから `sys.exit(1)` する実装済み。

---

### Fix-7: `Recipe.load()` にスキーマ検証を追加 ✅

**問題**
壊れた JSON や旧バージョンの `recipe.json` を読むと `KeyError` でクラッシュする。

**対象ファイル**
- `core/recipe/schema.py:88-97`

**対応済み**: `json.JSONDecodeError` ハンドリング・バージョン互換チェック・`KeyError` ハンドリングがすべて実装済み。

---

### Fix-8: Export を別スレッドで実行 ✅

**問題**
`_on_export()` がメインスレッドでファイル書き込みを実行するため、大きな WAV ファイル保存時に GUI がフリーズする。

**対象ファイル**
- `gui/worker.py` — `ExportWorker` クラスを追加
- `gui/main_window.py:289-309` — `ExportWorker` を使うように変更

**対応済み**: `ExportWorker` クラスが実装済みで、`main_window.py` の `_on_export()` で使用されている。

---

### Fix-9: `rubberband` コマンドの存在チェック ✅

**問題**
`pyrubberband` は内部で `rubberband` CLI を subprocess 呼び出しする。インストールされていない場合のエラーが cryptic。

**対象ファイル**
- `core/renderer/rubberband_renderer.py`

**対応済み**: モジュールロード時に `shutil.which("rubberband")` を確認し、なければ `RuntimeError` を raise する実装済み。

---

## 優先度3 — Minor（品質向上）

### Fix-10: モデルキャッシュの実装 ✅

**問題**
Demucs、RMVPE、beat_this が呼び出しごとに再ロードされる。

**対象ファイル**
- `core/separation/demucs_wrapper.py`
- `core/pitch/rmvpe_wrapper.py`
- `core/onset/beat_tracker.py`

**対応済み**: 3ファイルすべてにモジュールレベルのシングルトンキャッシュが実装済み。

---

### Fix-11: テストのアサーションを改善 ✅

**問題**
`test_beat_tracker` の `assert len(beats) >= 0` は常に真なので実質テストしていない。

**対象ファイル**
- `tests/test_integration.py:97`

**対応済み**: `assert isinstance(beats, np.ndarray)` と `assert isinstance(downbeats, np.ndarray)` に変更済み。

---

## 変更ファイル一覧

| ファイル | Fix # | ステータス |
|---------|-------|-----------|
| `core/recipe/generator.py` | Fix-1 | ✅ |
| `core/pitch/rmvpe_wrapper.py` | Fix-1, Fix-2 | ✅ |
| `core/renderer/rubberband_renderer.py` | Fix-3, Fix-9 | ✅ |
| `cli/main.py` | Fix-1, Fix-4, Fix-6 | ✅ |
| `gui/worker.py` | Fix-1, Fix-4, Fix-8 | ✅ |
| `gui/main_window.py` | Fix-5, Fix-8 | ✅ |
| `core/recipe/schema.py` | Fix-7 | ✅ |
| `core/separation/demucs_wrapper.py` | Fix-10 | ✅ |
| `core/onset/beat_tracker.py` | Fix-10 | ✅ |
| `tests/test_integration.py` | Fix-11 | ✅ |
