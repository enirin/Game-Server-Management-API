# Game Server Management API

`Game Server Management API` は Docker コンテナと Linuxネイティブプロセスの両方を管理できる Flask API です。
`api_contract.md` に記載したAPI仕様に合わせて、以下のエンドポイントを提供します。

- `GET /list`
- `POST /start/{server_name}`
- `POST /stop/{server_name}`

デフォルトの Base URL は `http://localhost:5000` です。`config.yaml` の `api.port` で変更できます。

## 利用者向け資料

- Discord連携を含む構築例: `DISCORD_GAME_SERVER_MANAGEMENT_GUIDE.md`

## アプリケーション概要

このAPIは、`config.yaml` に定義した複数サーバーを管理対象として扱います。

- サーバー一覧と状態の取得
- Docker / ネイティブプロセスの起動
- Docker / ネイティブプロセスの停止
- 各ゲームサーバーコンテナログのリアルタイム標準出力
- ログからのログイン/ログアウト検知と Discord Bot `/tell` 連携

`/list` の返却項目は `api_contract.md` の `ServerStatus` に準拠しています。

## 前提条件

- Linux
- Python 3.10+
- Docker対象サーバーがある場合は Docker がインストール済みかつ起動中
- Docker対象サーバーがある場合は API実行ユーザーが Docker デーモンにアクセス可能

## 初回セットアップ

```bash
cd /path/to/Game-Server-Management-API
/usr/bin/python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp config.yaml.sample config.yaml
```

`config.yaml` を編集して、管理対象サーバーを実環境に合わせて設定してください。

## モジュール構成

分割後の主要モジュールは以下です。

- `main.py`: Flaskアプリのエントリポイント。ルーティングとモジュール接続のみ担当
- `config_loader.py`: `config.yaml` の読み込み・バリデーション・正規化
- `server_runtime.py`: サーバー状態取得、および `start/stop` 実行ロジック（docker/native）
- `log_watcher.py`: リアルタイムログ追従、ログ解析器呼び出し、Discord `/tell` 通知トリガー
- `games/`: ゲーム固有プラグイン群のルート
- `games/<plugin_name>/plugin.py`: ゲーム固有のログ解析、日数抽出、tell向け文面生成
- `games/<plugin_name>/MAINTENANCE.md`: ゲーム別の保守仕様、実ログ例、通知方針
- `games/registry.py`: `game` エイリアスとプラグインの対応表
- `log_parsers.py`: 旧インポート互換レイヤー（新規実装では原則未使用）
- `discord_notifier.py`: `/tell` 送信と共通プロンプト組み立て

## 新しいゲーム対応（コントリビュータ向け）

別ゲームへ対応するPRは、基本的に `games/` 配下の追加だけで完結できます。

1. `games/<plugin_name>/plugin.py` を追加し、`GamePlugin` を継承したクラスを実装
2. `parse_presence_event()` にログイン/ログアウト検知ロジックを実装
3. 必要なら `extract_day()` をゲーム固有フォーマットに合わせてオーバーライド
4. `games/registry.py` の `PLUGIN_CLASSES` と `ALIASES` に登録
5. `config.yaml` の `servers[].game` にエイリアスを設定して動作確認

ゲーム別の判断基準や通知文面例は、各 `games/<plugin_name>/MAINTENANCE.md` に記載します。

この構成により、既存の API ルーティングや runtime 制御コードを触らずに機能拡張できます。

## config.yaml 形式

```yaml
api:
  port: 5000

discord:
  tell_url: http://127.0.0.1:5050/tell
  web_endpoint_token: ""
  request_timeout_sec: 5

servers:
  - server_id: 7d2d
    game: 7days2die
    runtime: native
    address: 192.168.1.10
    max_players: 8
    log_file_path: /opt/7d2d/Logs/output_log__2026-03-12__00-00-00.txt
    process_name: 7DaysToDieServer.x86_64
    status_command: pgrep -f 7DaysToDieServer.x86_64
    start_command: /opt/7d2d/startserver.sh
    stop_command: /opt/7d2d/stopserver.sh
    channel_id: 123456789012345678

  - server_id: valheim
    game: valheim
    runtime: docker
    container_name: valheim-server01
    address: 192.168.1.11
    max_players: 10
```

各項目の意味:

- `server_id`: API上の識別名 (`/start/{server_name}` の `server_name`)
- `game`: ログ解析器の種別 (`7days2die` / `7d2d` / `7daystodie` または `valheim`)
- `runtime`: `docker` または `native`（省略時は `docker`）
- `container_name`: Docker 上のコンテナ名（`runtime=docker` のとき必須）
- `address`: クライアント向け表示用アドレス
- `max_players`: 最大プレイヤー数（`players` の右側に使用）
- `channel_id` (任意): `/tell` に送る Discord チャンネルID。省略時は Bot 側既定値
- `log_file_path`: 監視ログファイルのパス（`runtime=native` のとき必須）
- `process_name` (任意): ネイティブプロセス名。`status_command` 未指定時の稼働判定に使用
- `status_command` (任意): 実行終了コード0で online 判定
- `start_command` (任意): `POST /start/{server_name}` で実行するコマンド
- `stop_command` (任意): `POST /stop/{server_name}` で実行するコマンド

`discord` セクションの意味:

- `tell_url`: Discord Bot の `/tell` エンドポイント
- `web_endpoint_token`: Bot 側に設定した場合、`X-Send-Token` ヘッダで送る値
- `request_timeout_sec`: `/tell` 呼び出しのタイムアウト秒

`api` セクションの意味:

- `port`: このAPIが待ち受けるポート番号

## 起動方法

`start.sh` は次を自動で実行します。

- (Git 管理下の場合) `git pull origin main`
- `venv` が無ければ作成
- `requirements.txt` をインストール
- `config.yaml` が無ければ `config.yaml.sample` から作成して停止
- API サーバーを起動

```bash
cd /path/to/Game-Server-Management-API
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
- `day` は `runtime=docker` の場合はコンテナログ、`runtime=native` の場合は `log_file_path` 末尾から抽出します。
- API起動中は、`runtime=docker` はコンテナログ、`runtime=native` はログファイル追従でリアルタイム出力します。
- `7dtd` と `valheim` はそれぞれ専用のログ解析ロジックを分離実装しており、接続ノイズを除外してログイン/ログアウト確定イベントだけを `/tell` 通知に使います。
- tellへ流す文面はゲームプラグイン側で組み立てるため、ゲームごとに歓迎/退出メッセージの方針を調整できます。
