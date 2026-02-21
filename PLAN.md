# pichi 実装計画

> ボーカルエディット自動化ツール — 設計・実装ロードマップ

---

## このドキュメントについて

本書は「要件定義」を受けて、実際にコードを書き始めるための実装計画をまとめたものです。
**何をどの順番で作るか**、**なぜその技術を選ぶか**、**どこでリスクが出るか** を一本の線で語ります。

---

## 1. アプリが解く問題

Mix作業において、ボーカルのピッチ補正とタイミング調整は最も時間がかかる工程です。
特に「同じ曲を別の歌い手が歌った」ケースでは、声域・語尾・子音・ブレスすべてがズレるため、既存のピッチ補正ツールだけでは対応しきれません。

pichi は **リファレンス音源（過去のMixまたはVocal Stem）と新規ドライボーカルを比較・解析し、補正済みWAVと編集レシピ（JSON）を自動生成**します。
ゴールは **pichi だけで完結すること**。外部ツールへの手渡しを前提とせず、残り2割の手直しも pichi の UI 上で行います。

---

## 2. 処理の流れ（パイプライン全体）

```
[入力]
  リファレンス（2mix or Vocal Stem）
  新規ドライボーカル
       ↓
[Step 1] ボーカル分離（2mix の場合のみ）
       ↓
[Step 2] 解析
  - F0（ピッチカーブ）
  - オンセット（発声タイミング）
  - 無声音・ブレス区間の推定
       ↓
[Step 3] アライメント
  - 拍・テンポ構造（第1軸）
  - F0・スペクトル特徴（第2軸）
       ↓
[Step 4] 編集レシピ生成（recipe.json）
  - タイムワープマップ
  - 目標ピッチカーブ
  - 区間ごとの信頼度（confidence）と補正強度
  - 破綻リスク区間の警告
       ↓
[Step 5] レンダリング（適用）
  - タイムストレッチ
  - ピッチシフト
  - 子音・無声音の保護
       ↓
[出力]
  edited_vocal.wav
  recipe.json
```

---

## 3. 補正戦略：confidence レベルごとの処理

confidence の高低で「どこまで追従するか」を変えることで、破綻を防ぎながら全区間に補正をかけます。
**スキップは行いません。**

| confidence | 補正内容 |
|---|---|
| 高（0.8+） | リファレンス F0 カーブに追従。タイミングも完全補正 |
| 中（0.5〜0.8） | カーブ追従を弱めて適用。タイミングも比例して弱める |
| 低（0.5未満） | **グローバルキーシフトのみ適用**（フレーズ単位の追従なし）。タイミングは最小限のみ |

低信頼区間でも「フレーズの細かい揺れは追わないが、キー差だけは修正する」という最低限の補正を維持します。
残った違和感は pichi の UI 上でセグメントごとに強度を調整して対処します。

---

## 4. 技術選定と理由

### ボーカル分離：Demucs v4（htdemucs）

2mix からボーカルを抽出する工程。
htdemucs はハイブリッド Transformer モデルで、現時点で公開されているオープンソースの分離モデルの中では音質・実績ともに最も安定しています。
将来的にモデルを MDX 系など他のものに差し替えられるよう、インターフェースは抽象化して持ちます。

Stem（vocal stem）が用意できる場合はこのステップをスキップします。精度が上がるため、運用上は Stem 入力を推奨します。

### ピッチ（F0）推定：rmvpe（スタンドアロン）→ torchcrepe

`pip install rmvpe` で導入できるスタンドアロン実装（yxlllc/RMVPE）を使用します。
RVC リポジトリ全体をクローンする方法は数 GB の不要な依存を抱えるため採用しません。

ポリフォニック環境（伴奏の残渣がある状態）でもボーカルの F0 を安定して取れることを目的に設計されたモデルで、分離残渣のある 2mix ルートで特に効果を発揮します。
バックアップとして torchcrepe を用意し、RMVPE が合わないケースで切り替えられるようにします。

### キーシフト自動検出

`global_key_shift_semitones` はリファレンスと新規ボーカルの **F0 中央値を比較**してセミトーン差を自動推定します。
推定値は UI 上で手動上書き可能にし、自動推定が外れた場合に即座に対処できるようにします。

```
key_shift = round(12 * log2(median(ref_f0) / median(new_f0)))
```

### ビート追跡：beat_this　／　オンセット検出：librosa

ビート追跡には 2024 年公開のニューラルビートトラッカー **beat_this** を使用します。
`librosa.beat.beat_track` は信号処理ベースで変拍子・テンポ揺れのある楽曲で精度が落ちるため、ビート追跡には採用しません。

オンセット検出（発声立ち上がりの検出）は引き続き `librosa.onset.onset_detect` を使用します。

```bash
pip install beat-this   # ビート追跡
# librosa はオンセット検出のみ使用
```

### アライメント：dtw-python（Sakoe-Chiba バンド制約付き）

別の歌い手が同じ曲を歌うケースでは、「構成は一致しているが歌い回しがズレている」状態になります。
DTW は F0 カーブとオンセット列を特徴量として、リファレンスと新規ボーカルの対応点を求めます。

`librosa.sequence.dtw` ではなく **`dtw-python`** を使用します。
5分曲を 100fps で計算するとコスト行列が 30,000 × 30,000 になり約 3.6GB のメモリを消費するため、**Sakoe-Chiba バンド制約**（`window_type="sakoechiba"`）でバンド幅を全体の 10% に制限します。

```bash
pip install dtw-python
```

一致度が低い区間は confidence スコアとして記録し、補正戦略（上表）を自動で選択します。

### 変換適用：pyrubberband（公式 C 拡張）

タイムストレッチとピッチシフトの中核。音楽制作向けに設計された高品質ライブラリで、子音の劣化を最小限に抑えながら変換できます。

`pyrubberband` は内部で rubberband CLI を subprocess 呼び出しするラッパーであり、セグメントが数十個になると起動オーバーヘッドが積み重なるため採用しません。
公式の Python C 拡張である **`pyrubberband`** を使用します。

```bash
pip install pyrubberband   # brew install rubberband が必要
```

### 有声/無声検出：librosa ルールベース → webrtcvad

`protect_unvoiced` フラグが示す無声区間（子音・ブレス）の検出は 2 段階で行います。

1. **librosa ベース**（MVP）：ゼロ交差率 + RMS エネルギーのしきい値判定
2. **webrtcvad**（精度が足りない場合に追加）：Google の WebRTC VAD、軽量で Python バインディングあり

```bash
pip install webrtcvad   # 必要になったタイミングで追加
```

### GUI：PySide6（MVP）→ JUCE（Phase 3+）

VST3 化を見据えると最終的には JUCE 一択ですが、MVP 段階での Python パイプラインとの統合速度を優先して、まず PySide6 で GUI を作ります。
解析エンジンと GUI を `recipe.json + WAV` という明確な入出力で分離しているため、GUI フレームワークを後で置き換えても内部ロジックは変わりません。

### 推論ランタイム：PyTorch（MVP）→ ONNX Runtime（配布時）

開発中は PyTorch のまま検証します。Win/mac の配布では依存関係が重くなるため、配布ビルドでは ONNX Runtime に変換して安定化します。

---

## 5. プロジェクト構成

```
pichi/
├── core/
│   ├── audio_io.py               # WAV/AIFF 読み書き・サンプルレート正規化
│   ├── separation/
│   │   └── demucs_wrapper.py
│   ├── pitch/
│   │   ├── rmvpe_wrapper.py      # pip install rmvpe（yxlllc/RMVPE）
│   │   └── torchcrepe_wrapper.py
│   ├── onset/
│   │   ├── beat_tracker.py       # beat_this（ニューラルビート追跡）
│   │   ├── onset_detector.py     # librosa（オンセット検出）
│   │   └── voiced_detector.py    # librosa ルールベース → webrtcvad
│   ├── key_detector.py           # F0 中央値比較によるキーシフト自動推定
│   ├── alignment/
│   │   └── dtw_aligner.py        # dtw-python + Sakoe-Chiba バンド制約
│   ├── recipe/
│   │   ├── schema.py             # dataclass + JSON Schema
│   │   └── generator.py
│   └── renderer/
│       └── rubberband_renderer.py  # pyrubberband（公式 C 拡張）
├── cli/
│   └── main.py
├── gui/
│   ├── app.py                    # PySide6 メインウィンドウ
│   └── widgets/
│       ├── pitch_view.py         # ピッチ3カーブビュー（インタラクティブ）
│       └── timeline_view.py      # 波形 + confidence ヒートマップ
├── schemas/
│   └── recipe.v1.json
├── tests/
└── pyproject.toml
```

---

## 6. recipe.json スキーマ（確定版）

recipe.json はこのツールの**中心資産**です。GUI 改善・VST3 移行・バッチ処理のどの方向に進んでも、この形式を維持することで互換性を保てます。

```json
{
  "version": "0.1",
  "sample_rate": 44100,
  "global_key_shift_semitones": 0.0,
  "segments": [
    {
      "t0": 0.0,
      "t1": 2.5,
      "time_warp_points": [
        [0.0, 0.0],
        [1.2, 1.35],
        [2.5, 2.5]
      ],
      "pitch_target_curve": [
        [0.0, 220.0],
        [0.5, 246.9],
        [1.0, 220.0]
      ],
      "confidence": 0.85,
      "pitch_strength": 1.0,
      "time_strength": 1.0,
      "protect_unvoiced": true
    }
  ],
  "warnings": [
    {
      "t0": 5.2,
      "t1": 5.8,
      "reason": "low_confidence",
      "detail": "フェイク差が大きい。グローバルキーシフトのみ適用"
    }
  ]
}
```

| フィールド | 説明 |
|---|---|
| `global_key_shift_semitones` | 別歌唱でキー差がある場合の全体シフト |
| `time_warp_points` | `[入力時刻, 出力時刻]` の対応点列 |
| `pitch_target_curve` | `[時刻, Hz]` の目標ピッチカーブ（Hz 絶対値、視覚化しやすいため） |
| `confidence` | DTW の一致度（0〜1）。補正戦略の自動選択に使う |
| `pitch_strength` | ピッチ補正の強さ（0〜1）。UI スライダーで上書き可能 |
| `time_strength` | タイミング補正の強さ（0〜1）。UI スライダーで上書き可能 |
| `protect_unvoiced` | 子音・ブレス区間をタイムストレッチから保護するフラグ |
| `warnings` | 破綻リスク区間。GUI でハイライト表示に使う |

> **設計メモ：** `pitch_strength` / `time_strength` はエンジンが confidence から自動計算した初期値を持ちます。
> UI スライダーで変更するとこの値が上書きされ、再レンダリング時に反映されます。

---

## 7. 視覚確認パネルの仕様（Phase 1 MVP に含める）

処理後に何が変わったか・どこを手直しするかが pichi 内で完結して分かる状態を Phase 1 から作ります。

### ピッチビュー（上段）

```
Hz（対数スケール）
 ─────────────────────────────────────────── 時間 →
  ── リファレンス F0   （青）
  ── 補正前 新規 F0    （赤）
  ── 補正後 新規 F0    （緑）

  [低信頼区間] ████████ オレンジ背景でハイライト
```

- 3カーブ重ね表示で「どこがどう動いたか」を即座に確認
- confidence が 0.5 未満の区間はオレンジ背景
- セグメントをクリック → 強度スライダーが表示される

### タイムラインビュー（下段）

```
 ─────────────────────────────────────────── 時間 →
  ████████████████████████████  波形（新規vocal）
  [0.9][0.9][0.7][0.4][0.8][0.9]  confidence ヒートマップ
```

- セグメントを confidence で色分け（緑→黄→オレンジ→赤）
- ピッチビューと再生カーソルを同期

### 補正強度スライダー（Phase 1 に含める）

```
選択中セグメント: 5.2s 〜 5.8s  confidence: 0.31
  ピッチ強度  ──●────────  0.3
  タイム強度  ──●────────  0.2
              [再レンダリング]
```

- スライダー変更 → `pitch_strength` / `time_strength` を recipe.json に書き込み → 再レンダリング → ビュー更新
- このループを pichi 内で完結させることで、外部ツール不要にする

---

## 8. 実装マイルストーン

### Phase 0：パイプライン検証

**目標：** 1曲でエンド・トゥ・エンドが動くことを確認する

やること：
- Python 環境構築（conda + pyproject.toml で再現可能な形に）
- `audio_io` → `separation` → `pitch` → `onset` → `alignment` → `recipe` → `renderer` を順番に実装
- CLI で `pichi run --ref reference.wav --vocal new_vocal.wav` が動く状態にする
- 出力 WAV を DAW に読み込んで品質を主観評価

成功の判断基準：
- 手直しが必要な箇所が「曲全体」ではなく「局所的な数箇所」に絞られること
- 子音・ブレスが明確に崩れていないこと

---

### Phase 1：MVP（スタンドアロンアプリ）

**目標：** 処理・確認・手直しが pichi 内で完結する最小限のアプリ

やること：
- PySide6 で GUI 構築（ファイル選択 / 2mix or Stem 切り替え / プリセット / 実行 / ログ）
- プリセット（軽め / 標準 / 強め）— confidence 閾値と初期 pitch_strength / time_strength のセット
- **ピッチビュー + タイムラインビュー（視覚確認）**
- **セグメントごとの強度スライダー + その場で再レンダリング**
- WAV + recipe.json の保存

---

### Phase 2：実用化

**目標：** 実際の Mix セッションで繰り返し使える完成度にする

やること：
- ピッチカーブの直接ドラッグ編集（より細かい手直し）
- バッチ処理（複数テイクの一括処理）
- エラー耐性：無音・ノイズ・分離失敗でクラッシュしない
- 処理速度の改善（GPU 活用）

---

### Phase 3：配布品質（Win/mac）

**目標：** 他の人に渡せるバイナリを作る

やること：
- 推論モデルを ONNX Runtime へ移行（Win/mac で統一配布）
- バイナリ化（pyinstaller or cx_Freeze）
- GUI を JUCE へ移行（VST3 準備）
- mac：arm64 + x86_64 Universal Binary、署名・公証（Notarization）
- Windows：インストーラー（Inno Setup）

---

### Phase 4：VST3

**目標：** DAW プラグインとして動作する

設計方針：
- **重い処理（分離・解析）はスタンドアロン/CLI に委託** し、recipe.json を生成
- プラグイン（JUCE + Steinberg VST3 SDK）は recipe.json を読み込んで適用 + 強度調整に専念
- DAW のプロジェクト上でリアルタイムプレビューしながら調整できる

---

## 9. リスクと対策

| リスク | 発生条件 | 対策 |
|---|---|---|
| 分離精度が低い | リファレンスが複雑な 2mix | Stem 入力を最優先運用。分離モデルを差し替え可能にしておく |
| アライメント破綻 | フェイクや語尾の歌い回しが大きく違う | F0 + オンセット多段 DTW。低信頼区間はキーシフトのみに自動縮退 |
| 子音の崩れ | タイムストレッチ量が大きい区間 | 無声音検出 + protect_unvoiced フラグで保護。母音中心に補正を適用 |
| mac 配布の詰まり | PyTorch の arm64 依存 | MVP は WAV/AIFF 限定で依存を最小化。ONNX Runtime で安定化 |
| キー差による精度低下 | 別歌唱でキーが違う | global_key_shift_semitones で事前補正してからアライメントへ渡す |

---

## 10. 着手順序（推奨）

```
1. recipe.json スキーマ確定（schemas/recipe.v1.json）
      ↓
2. Phase 0 — audio_io.py から始めてパイプラインを1本通す
      ↓
3. CLI で動作確認（1曲で評価）
      ↓
4. Phase 1 — ピッチビュー＋強度スライダー込みの GUI を乗せる
```

recipe.json を最初に確定させる理由は、これが各モジュール間の**唯一の契約**だからです。スキーマが固まっていれば、各モジュールを独立して開発・テストできます。

---

## 11. 開発環境セットアップ

```bash
# 環境作成（Python 3.11 推奨）
conda create -n pichi python=3.11
conda activate pichi

# Python 依存インストール（全て pip で完結）
pip install \
  torch torchaudio \        # 推論基盤
  demucs \                  # ボーカル分離
  rmvpe \                   # F0 推定（スタンドアロン）
  torchcrepe \              # F0 推定バックアップ
  beat-this \               # ニューラルビート追跡
  librosa \                 # オンセット検出・音声解析
  dtw-python \              # DTW アライメント
  pyrubberband \       # タイムストレッチ・ピッチシフト（C 拡張）
  soundfile \               # WAV/AIFF 読み書き
  PySide6 \                 # GUI フレームワーク
  pyqtgraph                 # 波形・ピッチ可視化

# webrtcvad は有声/無声検出の精度が足りない場合に追加
# pip install webrtcvad
```

> **注意：** `pyrubberband` は C 拡張のため、インストール時にビルドツールが必要です。
> - mac：`xcode-select --install` が通っていれば問題なし
> - Windows：Visual Studio Build Tools が必要

**動作確認 OS：**
- macOS 14+ (Apple Silicon / Intel)
- Windows 11

---

## 12. ライブラリ選定サマリー

| コンポーネント | ライブラリ | 選定理由 |
|---|---|---|
| ボーカル分離 | `demucs`（htdemucs） | オープンソース最高品質・モデル差し替え可能 |
| F0 推定（第一） | `rmvpe` | ポリフォニック環境でも安定・スタンドアロンで導入が軽い |
| F0 推定（第二） | `torchcrepe` | RMVPE が合わないケースのバックアップ |
| キーシフト検出 | F0 中央値比較（自前実装） | 外部ライブラリ不要・シンプルで十分な精度 |
| ビート追跡 | `beat-this` | ニューラル、2024 年時点で最良の精度 |
| オンセット検出 | `librosa` | beat_this でカバーされない発声立ち上がり検出に使用 |
| 有声/無声検出 | `librosa` ルールベース → `webrtcvad` | 段階的に精度を上げる構成 |
| アライメント | `dtw-python` | バンド制約対応、librosa.dtw より柔軟 |
| 変換適用 | `pyrubberband` | 公式 C 拡張・subprocess なし・本番品質 |
| GUI | `PySide6` + `pyqtgraph` | Python との統合が最速、後で JUCE に移行可能 |
| 推論ランタイム | `PyTorch` → `ONNX Runtime` | 開発は PyTorch、配布は ONNX で安定化 |

---

*最終更新：2026-02-21*
