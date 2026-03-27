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

### 2.　コンテナの起動
```bash
docker compose up -d --build
```
### 3.　アプリへのアクセス
Frontend (UI): http://localhost

Backend API (Swagger UI): http://localhost:8000/docs
※ APIの動作確認やデバッグに便利です。

## ディレクトリ構成
```bash
.
├── .env                 # 環境変数の設定ファイル
├── .gitignore           # GitHubにアップロードしないファイル（db, pycache等）の設定
├── app
│   ├── back             # 【Backend】FastAPI アプリケーション
│   │   ├── routers      # APIエンドポイントのディレクトリ（機能ごとに分割）
│   │   └── schemas.py   # Pydantic モデル（APIの入出力バリデーション定義）
│   └── front            # 【Frontend】静的ファイル（Nginxで配信）
│       ├── public
│       │   └── index.html # メインのHTMLファイル
│       └── src
│           ├── css
│           └── js       # JSでのフロント描画ロジック
├── docker-compose.yml   # 複数コンテナ（Backend, Frontend）の起動定義
├── Dockerfile           # アプリケーション実行環境の構築手順
├── instance             # DBの実ファイルなど、実行時に生成されるインスタンスデータ
├── nginx.conf           # フロントエンド配信用の Nginx 設定ファイル
├── README.md            # プロジェクト概要・セットアップ手順書
└── requirements.txt     # Pythonの依存ライブラリ一覧
```

