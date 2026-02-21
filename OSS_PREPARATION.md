# OSS 公開準備チェックリスト

Lyra をオープンソースとして公開するにあたり必要な準備事項をまとめます。

---

## 完了済み ✅

| # | 作業 | ファイル |
|---|------|---------|
| 1 | MIT License を追加 | `LICENSE` |
| 2 | `.gitignore` を整備（`models/*.pt`, `.venv/` 除外） | `.gitignore` |
| 3 | `pyproject.toml` にメタデータ追加（classifiers, license, keywords, URLs） | `pyproject.toml` |
| 4 | 依存名の修正（`rubberband-python` → `pyrubberband`） | `pyproject.toml` |
| 5 | `README.md` を作成 | `README.md` |
| 6 | `CONTRIBUTING.md` を作成 | `CONTRIBUTING.md` |
| 7 | `CHANGELOG.md` を作成 | `CHANGELOG.md` |
| 8 | `SECURITY.md` を作成 | `SECURITY.md` |
| 9 | `NOTICE` を作成（サードパーティ著作権・GPL 注記） | `NOTICE` |
| 10 | GitHub Actions CI を設定（3OS × Python 3.11/3.12） | `.github/workflows/ci.yml` |
| 11 | Issue / PR テンプレートを作成 | `.github/ISSUE_TEMPLATE/`, `.github/PULL_REQUEST_TEMPLATE.md` |
| 12 | Dependabot を設定 | `.github/dependabot.yml` |
| 13 | ruff lint 全エラーを解消 | 複数ファイル |
| 14 | smoke テスト 9/9 通過確認 | `tests/test_smoke.py` |
| 15 | PRODUCTION_FIXES.md 全11項目 実装済みを確認 | `PRODUCTION_FIXES.md` |
| 16 | `要件定義` → `docs/design_notes.md` に移動 | `docs/design_notes.md` |
| 17 | git リポジトリ初期化・初回コミット（`main` ブランチ） | — |

---

## GitHub 公開前に手動対応が必要 ⚠️

### 必須

- [ ] **`LICENSE`** — `Lyra Contributors` を実際の著作権者名に変更
- [ ] **`pyproject.toml` 等の `<owner>`** — 実際の GitHub ユーザー名/組織名に一括置換

  ```bash
  # 置換コマンド例
  grep -rl "<owner>" . --include="*.md" --include="*.toml" --include="*.yml" | \
    xargs sed -i '' 's/<owner>/your-github-username/g'
  ```

- [ ] **`pyrubberband`（GPL v2+）の対応方針を決定**（詳細は下記）

### 推奨

- [ ] GitHub リポジトリの About 欄を設定（Topics: `audio`, `vocal`, `python`, `music-production`）
- [ ] `main` ブランチの保護ルールを設定（PR 必須 + CI 必須）
- [ ] GitHub の Private vulnerability reporting を有効化

---

## ライセンスリスクについて

### pyrubberband（GPL v2+）と dtw-python（GPL v3+）

Lyra は **MIT License** で公開しますが、以下の依存が GPL です。

| パッケージ | ライセンス | 影響 |
|-----------|-----------|------|
| `pyrubberband` | GPL-2.0+ | タイムストレッチ・ピッチシフトに使用 |
| `dtw-python` | GPL-3.0+ | DTW アライメントに使用 |

**現在の対応**: `NOTICE` ファイルに詳細を明記済み。

**ユーザーへの影響**:
- Lyra を**そのまま使う**（コードを改変・配布しない）なら問題なし
- Lyra のコードを**クローズドソース製品に組み込む**場合はライセンス違反になる可能性あり

**将来的な代替案**（GPL から離れたい場合）:
- `pyrubberband` → `pedalboard`（Spotify製、GPL-free）または Rubber Band Library 商用ライセンス
- `dtw-python` → `tslearn` の DTW 実装（BSD-3-Clause）

### RMVPE モデル（`models/rmvpe.pt`）

モデルファイルの元リポジトリ（https://github.com/yxlllc/RMVPE）のライセンスを確認の上、`NOTICE` ファイルに正確な情報を記載してください。

---

## 将来の改善（任意）

- [ ] PyPI への公開（`pip install lyra` でインストール可能に）
- [ ] ドキュメントサイト（MkDocs / Read the Docs）
- [ ] `CODE_OF_CONDUCT.md`
- [ ] スクリーンショット・デモ動画を README に追加
- [ ] ONNX Runtime 化（推論の安定・高速化）
- [ ] Mac 署名・公証（Notarization）

---

## 参考

- [Choose a License](https://choosealicense.com/)
- [Keep a Changelog](https://keepachangelog.com/)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [GitHub: Creating a community profile](https://docs.github.com/en/communities)
- [Rubber Band Library 商用ライセンス](https://breakfastquay.com/rubberband/)
