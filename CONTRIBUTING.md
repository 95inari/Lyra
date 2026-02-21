# コントリビューションガイド

Lyra へのコントリビューションを歓迎します！
バグ報告・機能提案・ドキュメント改善・コード貢献、どんな形でも大歓迎です。

## 始める前に

- [Issue 一覧](https://github.com/<owner>/lyra/issues) を確認し、同様の報告・提案がないかチェックしてください
- 大きな変更を加える前に、まず Issue で議論することをお勧めします

## 開発環境のセットアップ

```bash
# リポジトリをフォーク後、クローン
git clone https://github.com/<your-name>/lyra.git
cd lyra

# 仮想環境を作成
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 開発用依存関係をインストール
pip install -e ".[dev]"

# モデルをダウンロード（統合テストを実行する場合）
python scripts/download_models.py --rmvpe
```

## テストの実行

```bash
# モデル不要のスモークテスト
pytest tests/test_smoke.py -v

# 統合テスト（モデルが必要）
pytest tests/test_integration.py -v

# 全テスト + カバレッジ
pytest --cov=core --cov=cli tests/ -v
```

## コーディングスタイル

```bash
# リント（ruff）
ruff check .

# 自動修正
ruff check --fix .
```

- Python 3.11 以上の構文を使用
- 1行の長さは 100 文字以内
- 型ヒントを積極的に使用

## プルリクエストの手順

1. `main` ブランチから作業ブランチを作成します

   ```bash
   git checkout -b fix/issue-123-description
   # または
   git checkout -b feat/new-feature-name
   ```

2. 変更を加え、テストが通ることを確認します

   ```bash
   pytest tests/test_smoke.py -v
   ruff check .
   ```

3. コミットメッセージは [Conventional Commits](https://www.conventionalcommits.org/) 形式を推奨します

   ```
   fix: ボーカル分離でステレオ音源が失敗する問題を修正
   feat: GUI にズーム機能を追加
   docs: README のインストール手順を更新
   refactor: F0 推定モジュールのキャッシュ処理を整理
   test: DTW アライメントの単体テストを追加
   ```

4. プルリクエストを作成し、変更内容を説明してください
   - 何を・なぜ変更したか
   - テスト方法
   - 関連する Issue 番号（例: `Closes #123`）

## バグ報告

Issue を作成する際は以下を含めてください:

- **環境情報**: OS、Python バージョン、GPU の有無
- **再現手順**: 最小限のコマンドや操作手順
- **期待する動作** と **実際の動作**
- **エラーメッセージ** や スタックトレース（あれば）
- 入力音声の特徴（サンプルレート、長さ、など）

## ライセンス

コントリビューションは [MIT License](LICENSE) のもとで公開されます。