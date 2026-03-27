# Craftopia プラグイン保守メモ

## 概要

Craftopia の dedicated server ログには、この API が安定して解釈できるログイン・ログアウト記録がほぼ出力されません。
そのため、このプラグインでは `tcpdump` などで生成した外部接続ログを使って在席監視を行います。

このリポジトリには、その接続ログを生成する補助スクリプトとして `games/craftopia/watch-craftopia-connections.sh` を同梱しています。

現在の Craftopia 運用は、`docker compose` でコンテナを起動しつつ、ゲーム本体のインストール先 `/opt/craftopia` はホスト側ディレクトリへ永続化する構成です。
そのため `kagurazakanyaa/craftopia:latest` は主に実行環境と `steamcmd` を提供する土台として使い、実際にログイン可否を左右するゲームビルド自体はホスト側の `app/` を更新して管理します。

## 想定する接続ログ形式

パーサは次のような行を読み取ります。

```text
2026-03-23 21:14:55 LOGIN 203.0.113.10:54000
2026-03-23 21:16:12 LOGOUT 203.0.113.10:54000 idle=8s
```

ヘッダー行や説明行など、形式に一致しない行は無視されます。

## 実装している挙動

- `parse_presence_event()` は `LOGIN` / `LOGOUT` 行を在席イベントに変換します。
- 接続元は `IP:port` ではなく `IP` に正規化し、共通マッピングに登録済みなら通知ではプレイヤー名を使います。
- `extend_server_status()` は接続ログを再生し、まだ退出していない接続元の数から現在人数を推定します。
- `day` は Craftopia のセーブ DB に入っている `WorldSave.latestDay` から読み取ります。
- `save_data_path` が未指定でも、`presence_log_path` または `log_file_path` の親ディレクトリ配下にある `data/Worlds/*.db` を自動検出できる構成では日数を読み取れます。

## 現在の Docker 構成

Compose 定義は [compose.yaml](./compose.yaml) を参照します。

この構成のポイントは次のとおりです。

- `container_name` は `craftopia-server` 固定で、API 側はこの名前を使って状態を見ます。
- `compose-entrypoint.sh` が `FORCE_UPDATE=true` のときだけ `steamcmd +app_update 1670340 validate` を実行します。
- ゲーム本体のインストール先は `CRAFTOPIA_INSTALL_DIR` で指定したホスト側ディレクトリを `/opt/craftopia` へ bind mount します。
- セーブデータは `CRAFTOPIA_DATA_DIR` を `/opt/craftopia/DedicatedServerSave` と `/opt/craftopiaDedicatedServerSave` へ bind mount します。
- BepInEx の config / plugins は named volume で持ちます。

運用上、`docker compose pull` は実行環境や `steamcmd` 側の更新には効きますが、ゲーム本体ビルドの更新は `CRAFTOPIA_INSTALL_DIR` 側の `steamcmd` 実行結果で決まります。

## 運用上の注意

- Docker 管理の Craftopia でも、コンテナの online / offline 状態や CPU / メモリ使用量は Docker 側から取得します。
- リアルタイム通知と現在人数の推定は、`servers[].presence_log_path` に指定したログファイルを使います。
- ゲーム内日数の取得元は標準出力ログではなくセーブ DB です。確実に読み取らせたい場合は `servers[].save_data_path` に `DedicatedServerSave` のホスト側パスを指定してください。
- プレイヤー名の登録は MCP の `register_ip_player_name` tool から行い、既定ではリポジトリ直下の `ip_player_map.txt` へ保存します。別パスにしたい場合は `GAME_SERVER_IP_PLAYER_MAP_PATH` を設定してください。
- 未登録の接続元は通知でも人数推定でも `IP` 単位で扱い、`port` は無視します。
- `CRAFTOPIA_INSTALL_DIR` を空ディレクトリへ向けると、image 側の `/opt/craftopia` は mount で隠れます。初回導入時は設定ファイルを明示的に作るか、image からコピーしてください。
- `docker compose pull && docker compose up -d` だけでは、クライアントとサーバーのゲームビルド差分は解消されない場合があります。

## 初回導入手順

### 1. tcpdump をインストールする

```bash
sudo apt update
sudo apt install -y tcpdump
```

### 2. サーバー配置先を作る

```bash
mkdir -p /home/enirin/game-servers/craftopia
mkdir -p /home/enirin/game-servers/craftopia/app
mkdir -p /home/enirin/game-servers/craftopia/data
```

### 3. 同梱ファイルを配置する

```bash
cp /path/to/Game-Server-Management-API/games/craftopia/watch-craftopia-connections.sh \
  /home/enirin/game-servers/craftopia/watch-craftopia-connections.sh
cp /path/to/Game-Server-Management-API/games/craftopia/compose.yaml \
  /home/enirin/game-servers/craftopia/docker-compose.yml
cp /path/to/Game-Server-Management-API/games/craftopia/compose-entrypoint.sh \
  /home/enirin/game-servers/craftopia/compose-entrypoint.sh
cp /path/to/Game-Server-Management-API/games/craftopia/.env.sample \
  /home/enirin/game-servers/craftopia/.env
chmod +x /home/enirin/game-servers/craftopia/watch-craftopia-connections.sh
chmod +x /home/enirin/game-servers/craftopia/compose-entrypoint.sh
```

### 4. `.env` を実環境に合わせて編集する

最低限、次は確認してください。

- `CRAFTOPIA_PORT`
- `CRAFTOPIA_INSTALL_DIR`
- `CRAFTOPIA_DATA_DIR`
- `CRAFTOPIA_SERVER_NAME`
- `CRAFTOPIA_HOST_MAX_PLAYERS`
- `CRAFTOPIA_HOST_USE_PASSWORD`
- `CRAFTOPIA_HOST_SERVER_PASSWORD`

### 5. 初回用の `ServerSetting.ini` を配置する

`CRAFTOPIA_INSTALL_DIR` が空の場合、image 側の `ServerSetting.ini` は bind mount で見えなくなります。
初回だけ次のどちらかを実行してください。

方法 A: image からテンプレートをコピーする

```bash
docker run --rm \
  -v /home/enirin/game-servers/craftopia/app:/work \
  --entrypoint /bin/bash \
  kagurazakanyaa/craftopia:latest \
  -lc 'cp -n /opt/craftopia/DefaultServerSetting.ini /work/DefaultServerSetting.ini && cp -n /opt/craftopia/ServerSetting.ini /work/ServerSetting.ini'
```

方法 B: すでに用意済みの `ServerSetting.ini` / `DefaultServerSetting.ini` を `app/` へ置く

### 6. 接続監視スクリプトを起動する

```bash
sudo /home/enirin/game-servers/craftopia/watch-craftopia-connections.sh 6587 \
  /home/enirin/game-servers/craftopia/craftopia-connections.log
```

root で直接起動しない場合、スクリプトは `sudo` 経由で `tcpdump` を実行しようとします。

### 7. Compose で起動する

```bash
cd /home/enirin/game-servers/craftopia
docker compose up -d
```

### 8. API の設定で生成ログとセーブデータを参照する

```yaml
servers:
  - server_id: craftopia
    game: craftopia
    runtime: docker
    container_name: craftopia-server
    address: 192.168.1.12:6587
    max_players: 8
    presence_log_path: /home/enirin/game-servers/craftopia/craftopia-connections.log
    save_data_path: /home/enirin/game-servers/craftopia/data
```

### 9. スクリプトを常駐させる

`systemd` サービス、`screen`、`tmux`、その他のプロセスマネージャーで常駐させる構成を推奨します。
API 側は生成されたログファイルを読むだけで、この補助スクリプト自体を起動する機能はありません。

## 通常起動と停止

起動:

```bash
cd /home/enirin/game-servers/craftopia
docker compose up -d
```

停止:

```bash
cd /home/enirin/game-servers/craftopia
docker compose stop
```

状態確認:

```bash
cd /home/enirin/game-servers/craftopia
docker compose ps
```

ログ確認:

```bash
cd /home/enirin/game-servers/craftopia
docker compose logs -f craftopia
```

## 更新手順

### 前提

現在の構成では、ゲーム本体ビルドの更新主体は `docker compose pull` ではなく `steamcmd` です。
`docker compose pull` はベース image の更新を取り込むだけで、クライアントとサーバーのゲームビルド差分を必ずしも埋めません。

### 推奨手順

1. セーブデータと必要なら `app/` をバックアップする

```bash
cp -a /home/enirin/game-servers/craftopia/data /home/enirin/game-servers/craftopia/data.backup-$(date +%F-%H%M%S)
cp -a /home/enirin/game-servers/craftopia/app /home/enirin/game-servers/craftopia/app.backup-$(date +%F-%H%M%S)
```

2. 必要ならベース image を更新する

```bash
cd /home/enirin/game-servers/craftopia
docker compose pull
```

3. `FORCE_UPDATE` を有効化する

```bash
cd /home/enirin/game-servers/craftopia
sed -i 's/^CRAFTOPIA_FORCE_UPDATE=.*/CRAFTOPIA_FORCE_UPDATE=true/' .env
```

4. Compose を再作成して `steamcmd` 更新を走らせる

```bash
cd /home/enirin/game-servers/craftopia
docker compose up -d --force-recreate
```

5. `appmanifest_1670340.acf` の `buildid` が新しい値へ切り替わるまで待つ

```bash
docker exec craftopia-server sh -lc 'sed -n "1,40p" /opt/craftopia/steamapps/appmanifest_1670340.acf | grep -E "buildid|TargetBuildID|BytesToDownload|BytesDownloaded"'
```

`buildid` と `TargetBuildID` が同じ新しい値になり、`BytesToDownload=0` になれば更新完了です。

6. `FORCE_UPDATE` を無効化して通常起動へ戻す

```bash
cd /home/enirin/game-servers/craftopia
sed -i 's/^CRAFTOPIA_FORCE_UPDATE=.*/CRAFTOPIA_FORCE_UPDATE=false/' .env
docker compose up -d --force-recreate
```

7. クライアント側も Steam で最新版へ更新してから再接続する

### 更新後の確認ポイント

- `docker compose ps` で `craftopia-server` が `Up` になっていること
- `docker inspect craftopia-server --format 'Status={{.State.Status}} ExitCode={{.State.ExitCode}}'` が `running / 0` であること
- `appmanifest_1670340.acf` の `buildid` と `TargetBuildID` が一致していること
- クライアント側も Steam で更新済みであること
- 接続できたあとに `presence_log_path` 側へ `LOGIN` が出ること

## トラブルシュート

### `docker compose pull && docker compose up -d` したのにログインできない

ベース image だけ新しくなっても、`CRAFTOPIA_INSTALL_DIR` に残っているゲーム本体ビルドが古い可能性があります。
`FORCE_UPDATE=true` での更新手順を実行し、`appmanifest_1670340.acf` の `buildid` を確認してください。

### `sed: can't read /opt/craftopia/ServerSetting.ini` で起動しない

`CRAFTOPIA_INSTALL_DIR` を空ディレクトリへ mount した直後に起きます。
`DefaultServerSetting.ini` と `ServerSetting.ini` を image からコピーしてから再起動してください。

### Shader 警告が大量に出る

GPU の無い Linux コンテナ上で Unity 系サーバーを動かしたときの警告で、今回の運用では基本的に無視しています。
コンテナが `running` を維持し、クライアントが接続できるなら、優先度は低いです。

### `craftopia-server` が更新中に長時間サーバー起動しない

`FORCE_UPDATE=true` 時は、`compose-entrypoint.sh` が `steamcmd` を完了させてから本来の `/docker-entrypoint.sh` を呼びます。
そのため更新中は PID 1 がサーバー本体ではなく wrapper のまま待機します。
`/home/steam/Steam/logs/content_log.txt` と `appmanifest_1670340.acf` を見て進捗を確認してください。

## 設定例

```yaml
servers:
  - server_id: craftopia
    game: craftopia
    runtime: docker
    container_name: craftopia-server
    address: 192.168.1.12:6587
    max_players: 8
    presence_log_path: /home/enirin/game-servers/craftopia/craftopia-connections.log
    save_data_path: /home/enirin/game-servers/craftopia/data
```