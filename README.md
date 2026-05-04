# BookMetter (読書管理アプリ)
このアプリは、読んだ本のページ範囲を記録し、進捗を視覚化することを目的に開発しています。

## 構成
- **Backend:** FastAPI (Python 3.11) + SQLAlchemy
- **Database:** SQLite
- **Frontend:** JavaScript + HTML/CSS
- **Infrastructure:** Docker / Docker Compose (Nginx)

## セットアップ手順
Docker がインストールされている環境であれば、以下の手順ですぐに開発を開始できます。

### 1. リポジトリのクローン
```bash
git clone git@github.com:yoshidaLTI/book-metter.git
cd book-metter
```

### 2. コンテナの起動
```bash
docker compose up -d --build
```

### 3. アプリへのアクセス
- Frontend (UI): http://localhost
- Backend API (Swagger UI): http://localhost:8000/docs

※ APIの動作確認やデバッグに便利です。

## テスト手順

### APIテストの実行
コンテナが起動している状態で以下を実行してください。

```bash
docker compose exec backend env PYTHONPATH=/app pytest app/test_code/test_api.py -v
```

### テスト結果をファイルに保存する場合
```bash
docker compose exec backend env PYTHONPATH=/app pytest app/test_code/test_api.py -v > test_result.txt 2>&1
```

### テスト対象
| クラス | 内容 |
|---|---|
| TestAuth | サインアップ・ログイン・認証・ログアウト |
| TestGroup | グループの作成・取得・検索 |
| TestMembership | グループへの参加・退会 |
| TestProgress | 進捗の記録・取得 |

## ディレクトリ構成
```
.
├── Dockerfile           # アプリケーション実行環境の構築手順
├── README.md            # プロジェクト概要・セットアップ手順書
├── docker-compose.yml   # 複数コンテナ（Backend, Frontend）の起動定義
├── nginx.conf           # フロントエンド配信用の Nginx 設定ファイル
├── requirements.txt     # Pythonの依存ライブラリ一覧
├── instance
│   └── reading_app.db   # SQLite データベースファイル（実行時に生成）
└── app
    ├── __init__.py
    ├── back             # 【Backend】FastAPI アプリケーション
    │   ├── main.py      # アプリのエントリーポイント・ルーター登録
    │   ├── models.py    # SQLAlchemy モデル（DBテーブル定義）
    │   ├── schemas.py   # Pydantic モデル（APIの入出力バリデーション）
    │   ├── crud.py      # DB操作ロジック
    │   ├── database.py  # DB接続設定
    │   ├── dependencies.py  # 認証などの共通依存関係
    │   ├── auth_utils.py    # パスワードハッシュ・セッション管理
    │   └── routers      # APIエンドポイント（機能ごとに分割）
    │       ├── auth.py      # 認証（signup / login / logout / me）
    │       ├── group.py     # グループ操作・進捗記録
    │       └── books.py     # Google Books API 連携
    ├── front            # 【Frontend】静的ファイル（Nginxで配信）
    │   ├── public       # HTMLファイル
    │   │   ├── index.html
    │   │   ├── login.html
    │   │   ├── group-detail.html
    │   │   ├── search-book.html
    │   │   ├── search-group.html
    │   │   └── bookshelf.html
    │   └── src
    │       ├── css
    │       ├── js
    │       │   ├── api.js   # バックエンドAPIとの通信関数
    │       │   └── main.js  # 認証・画面描画ロジック
    │       └── picture
    └── test_code        # APIテストコード
        ├── __init__.py
        └── test_api.py
```