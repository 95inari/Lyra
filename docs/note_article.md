# Lyra — ボーカルエディットを自動化するOSSを公開しました

## はじめに

ミックスで最も時間がかかる作業のひとつが、**ボーカルエディット（ピッチ補正・タイミング補正）** です。

「同じ曲を別の人が歌ったテイクを、リファレンスのピッチ/タイミングに近づける」作業を、手動でやると曲1曲あたり数時間かかることもあります。

これを自動化するPythonツール **Lyra** を作り、オープンソースとして公開しました。

GitHub: https://github.com/95inari/Lyra

---

## Lyra でできること

**入力**:
- リファレンス音源（2mix または Vocal Stem）
- 新規ドライボーカル

**出力**:
- 補正済みボーカル WAV
- 補正データ（recipe.json）

リファレンスのピッチカーブ・タイミングを解析し、新規ボーカルに自動で適用します。

「完璧な自動化」ではなく **「8割自動にして残り2割だけ手直し」** を目標に設計しています。

---

## 処理の仕組み

```
リファレンス音源
       ↓
① ボーカル分離（Demucs htdemucs）
       ↓
② F0推定（RMVPE）  ←── 新規ボーカルも同様に解析
       ↓
③ オンセット検出（librosa）
       ↓
④ キーシフト推定
       ↓
⑤ DTWアライメント  ←── タイミング・ピッチの対応付け
       ↓
⑥ レンダリング（Rubber Band Library）
       ↓
補正済みWAV + recipe.json
```

各処理で信頼度（confidence）を計算し、**アライメントが怪しい区間は自動で補正を弱める** 仕組みになっています。これにより「やりすぎ」による音質破綻を防いでいます。

---

## 技術スタック

| 処理 | ライブラリ |
|------|-----------|
| ボーカル分離 | [Demucs v4](https://github.com/facebookresearch/demucs)（htdemucs） |
| F0推定 | [RMVPE](https://github.com/yxlllc/RMVPE) |
| ビート・オンセット検出 | [librosa](https://librosa.org/)、[beat-this](https://github.com/superbock/beat-this) |
| タイミングアライメント | [dtw-python](https://dynamictimewarping.github.io/) |
| ピッチ・タイム補正 | [Rubber Band Library](https://breakfastquay.com/rubberband/)（pyrubberband経由） |
| GUI | [PySide6](https://doc.qt.io/qtforpython/)（Qt6） |

---

## 使い方

### CLIで使う

```bash
# インストール
git clone https://github.com/95inari/Lyra
cd Lyra
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .
python scripts/download_models.py --rmvpe

# 実行
lyra run --ref reference.wav --vocal new_vocal.wav
```

### GUIで使う

```bash
python -m gui.app
```

GUIではピッチカーブの可視化と、セグメントごとの補正強度の調整ができます。

---

## recipe.json とは

Lyra は補正データを `recipe.json` として出力します。

```json
{
  "version": "0.1",
  "global_key_shift_semitones": -2.0,
  "segments": [
    {
      "t0": 0.0, "t1": 2.5,
      "time_warp_points": [[0.0, 0.0], [1.2, 1.35], [2.5, 2.5]],
      "pitch_target_curve": [[0.0, 220.0], [0.5, 246.9]],
      "confidence": 0.85,
      "pitch_strength": 1.0,
      "time_strength": 1.0,
      "protect_unvoiced": false
    }
  ]
}
```

補正内容をデータとして分離することで、将来的に DAW プラグイン（VST3 等）でも同じレシピを再利用できるよう設計しています。

---

## 設計で気をつけたこと

### 子音・ブレスの保護

ピッチシフトを有声区間（母音）に限定し、子音やブレスには適用しないフラグ（`protect_unvoiced`）を実装しています。無声区間にピッチシフトをかけると音質が崩れるためです。

### 信頼度ベースの自動弱め

DTW のアライメント精度が低い区間は `confidence` スコアが下がり、補正強度（`pitch_strength` / `time_strength`）が自動で弱まります。ユーザーが意図しない過補正を防ぐ設計です。

### recipe.json の中心設計

補正ロジックと補正データを分離することで:
- GUI の改善や作り直しが、過去の補正データに影響しない
- 将来の DAW プラグイン化に対応できる
- 補正結果を人間が読める形で確認・編集できる

---

## 既知の課題

まだ v0.1.0 のアルファ版です。以下の点で手直しが必要なケースがあります:

- 歌い回しが大きく異なるフェイク・装飾音符でアライメントが外れることがある
- Demucs の分離残渣が多い音源では F0 精度が落ちる
- 処理時間は 5 分曲で CPU 数分、GPU で短縮可能

改善 PR や Issue を歓迎しています。

---

## 利用者の方へ

Lyra は DTM・音楽制作をしている方を主な対象にしています。

**こんな場面で役立ちます:**

- カバー曲やコラボで、別シンガーのボーカルをリファレンスのテイクに合わせたい
- 複数テイクを録り直したが、ピッチ・タイミングを統一してコンプしたい
- ボーカルエディットの下処理を自動化して、細かい手直しだけに集中したい

**使うときのコツ:**

- リファレンスは **分離済みの Vocal Stem** を渡すと精度が上がります（`--stem` フラグ）
- キーが明らかにずれている場合は `--key-shift` で手動指定するほうが安定します
- 結果が過補正に感じたら `--preset light` を試してください

**フィードバックについて:**

「こういうケースで外れた」「この音源で試したらうまくいった」という報告を GitHub の [Issues](https://github.com/95inari/Lyra/issues) に送っていただけると、改善に直結します。

---

## 開発者の方へ

Lyra はオーディオ処理・機械学習・GUI を組み合わせたプロジェクトです。Python に慣れている方であればすぐにコードを読めると思います。

**リポジトリ構成:**

```
core/          # 処理コア（分離・F0推定・アライメント・レンダリング）
cli/           # コマンドラインインターフェース
gui/           # PySide6 GUI
tests/         # スモークテスト・統合テスト
scripts/       # モデルダウンロードスクリプト
schemas/       # recipe.json スキーマ定義
```

**開発環境のセットアップ:**

```bash
git clone https://github.com/95inari/Lyra
cd Lyra
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python scripts/download_models.py --rmvpe

# テスト（モデル不要）
pytest tests/test_smoke.py -v

# リント
ruff check .
```

**特に助かる貢献:**

- アライメント精度の改善（フェイク・装飾音符対応）
- F0推定の後処理（オクターブ誤判定の修正）
- Windows 環境での動作確認・バグ修正
- GUI のUX改善

詳細は [CONTRIBUTING.md](https://github.com/95inari/Lyra/blob/main/CONTRIBUTING.md) をご覧ください。

---

## おわりに

まだ実用レベルには課題がありますが、「ボーカルエディットの自動化」というアプローチ自体は手応えを感じています。

音楽制作・ミックスエンジニアリング・Python オーディオ処理に興味がある方はぜひ触ってみてください。フィードバックも歓迎です。

GitHub: https://github.com/95inari/Lyra

---

*Lyra は MIT License で公開しています。ただし依存ライブラリに GPL ライセンスのものが含まれます（pyrubberband, dtw-python）。詳細は NOTICE ファイルをご確認ください。*
