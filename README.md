# Game Server Management API

`Game Server Management API` は Docker コンテナとして動作するゲームサーバーを管理する Flask API です。
`api_contract.md` に記載したAPI仕様に合わせて、以下のエンドポイントを提供します。

- `GET /list`
- `POST /start/{server_name}`
- `POST /stop/{server_name}`

デフォルトの Base URL は `http://localhost:5000` です。

## アプリケーション概要

このAPIは、`config.yaml` に定義した複数サーバーを管理対象として扱います。

- サーバー一覧と状態の取得
- Docker コンテナの起動
- Docker コンテナの停止
- 各ゲームサーバーコンテナログのリアルタイム標準出力
- ログからのログイン/ログアウト検知と Discord Bot `/tell` 連携

`/list` の返却項目は `api_contract.md` の `ServerStatus` に準拠しています。

## 前提条件

- Linux
- Python 3.10+
- Docker がインストール済みかつ起動中
- APIを実行するユーザーが Docker デーモンにアクセス可能

## 初回セットアップ

```bash
cd /home/enirin/work/gs-monitor
/usr/bin/python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp config.yaml.sample config.yaml
```

`config.yaml` を編集して、管理対象サーバーを実環境に合わせて設定してください。

## config.yaml 形式

```yaml
discord:
  tell_url: http://127.0.0.1:5050/tell
  web_endpoint_token: ""
  request_timeout_sec: 5

servers:
  - server_id: 7dtd
    game: 7dtd
    container_name: 7dtd-server01
    address: 192.168.1.10
    max_players: 8
    channel_id: 123456789012345678

  - server_id: valheim
    game: valheim
    container_name: valheim-server01
    address: 192.168.1.11
    max_players: 10
```

各項目の意味:

- `server_id`: API上の識別名 (`/start/{server_name}` の `server_name`)
- `game`: ログ解析器の種別 (`7dtd` または `valheim`)
- `container_name`: Docker 上のコンテナ名
- `address`: クライアント向け表示用アドレス
- `max_players`: 最大プレイヤー数（`players` の右側に使用）
- `channel_id` (任意): `/tell` に送る Discord チャンネルID。省略時は Bot 側既定値

`discord` セクションの意味:

- `tell_url`: Discord Bot の `/tell` エンドポイント
- `web_endpoint_token`: Bot 側に設定した場合、`X-Send-Token` ヘッダで送る値
- `request_timeout_sec`: `/tell` 呼び出しのタイムアウト秒

## 起動方法

`start.sh` は次を自動で実行します。

- (Git 管理下の場合) `git pull origin main`
- `venv` が無ければ作成
- `requirements.txt` をインストール
- `config.yaml` が無ければ `config.yaml.sample` から作成して停止
- API サーバーを起動

```bash
cd /home/enirin/work/gs-monitor
chmod +x start.sh
./start.sh
```

## API 仕様

### 1. サーバー一覧の取得

- `GET /list`
- 200 OK

```json
{
  "servers": [
    {
      "name": "7dtd-server-01",
      "status": "online",
      "address": "192.168.1.10",
      "stats": {
        "players": "0/8",
        "cpu": 12.5,
        "memory": 4.2
      },
      "day": 14
    }
  ]
}
```

### 2. サーバーの起動

- `POST /start/{server_name}`
- 200 OK

```json
{
  "success": true,
  "message": "Server '7dtd-server-01' is starting...",
  "server_name": "7dtd-server-01"
}
```

- 404 Not Found（`server_name` またはコンテナが存在しない場合）

### 3. サーバーの停止

- `POST /stop/{server_name}`
- 200 OK

```json
{
  "success": true,
  "message": "Server '7dtd-server-01' is stopping...",
  "server_name": "7dtd-server-01"
}
```

- 404 Not Found（`server_name` またはコンテナが存在しない場合）

## 補足

- `status` は `online` / `offline` / `busy` を返します。
- `players` の現在値はゲームごとの取得方法が異なるため、現状は `0/max_players` を返します。
- `day` はコンテナログから `Day <number>` または `Day: <number>` の最終値を抽出します。該当ログがない場合は `0` です。
- API起動中は、`config.yaml` で定義した各コンテナのログを `[server_id/container_name]` プレフィックス付きで標準出力に流します。
- `7dtd` と `valheim` はそれぞれ専用のログ解析ロジックを分離実装しており、ログイン/ログアウトを検知すると共通のプロンプト生成処理で `/tell` にPOSTします。
