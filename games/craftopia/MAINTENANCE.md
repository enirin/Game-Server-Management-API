# Craftopia プラグイン保守メモ

## 概要

Craftopia の dedicated server ログには、この API が安定して解釈できるログイン・ログアウト記録がほぼ出力されません。
そのため、このプラグインでは `tcpdump` などで生成した外部接続ログを使って在席監視を行います。

このリポジトリには、その接続ログを生成する補助スクリプトとして `games/craftopia/watch-craftopia-connections.sh` を同梱しています。

## 想定する接続ログ形式

パーサは次のような行を読み取ります。

```text
2026-03-23 21:14:55 LOGIN 203.0.113.10:54000
2026-03-23 21:16:12 LOGOUT 203.0.113.10:54000 idle=8s
```


ヘッダー行や説明行など、形式に一致しない行は無視されます。

## 実装している挙動

- `parse_presence_event()` は `LOGIN` / `LOGOUT` 行を在席イベントに変換します。
- `extend_server_status()` は接続ログを再生し、まだ退出していない接続元の数から現在人数を推定します。
- `day` は Craftopia のセーブ DB に入っている `WorldSave.latestDay` から読み取ります。
- `save_data_path` が未指定でも、`presence_log_path` または `log_file_path` の親ディレクトリ配下にある `data/Worlds/*.db` を自動検出できる構成では日数を読み取れます。

## 運用上の注意

- Docker 管理の Craftopia でも、コンテナの online / offline 状態や CPU / メモリ使用量は Docker 側から取得します。
- リアルタイム通知と現在人数の推定は、`servers[].presence_log_path` に指定したログファイルを使います。
- ゲーム内日数の取得元は標準出力ログではなくセーブ DB です。確実に読み取らせたい場合は `servers[].save_data_path` に `DedicatedServerSave` のホスト側パスを指定してください。
- この方式ではプレイヤーをゲーム内名ではなく接続元 endpoint で識別するため、Discord 通知にも endpoint が含まれます。

## 導入手順

### 1. tcpdump をインストールする

```bash
sudo apt update
sudo apt install -y tcpdump
```

### 2. 同梱スクリプトを Craftopia サーバー配置先へコピーする

現在の構成を前提にした配置例です。

```bash
mkdir -p /home/enirin/game-servers/craftopia
cp /path/to/Game-Server-Management-API/games/craftopia/watch-craftopia-connections.sh \
  /home/enirin/game-servers/craftopia/watch-craftopia-connections.sh
chmod +x /home/enirin/game-servers/craftopia/watch-craftopia-connections.sh
```

必要なら Compose 用の環境変数テンプレートも配置します。

```bash
cp /path/to/Game-Server-Management-API/games/craftopia/.env.sample \
  /home/enirin/game-servers/craftopia/.env
```

### 3. 接続監視スクリプトを起動する

```bash
sudo /home/enirin/game-servers/craftopia/watch-craftopia-connections.sh 6587 \
  /home/enirin/game-servers/craftopia/craftopia-connections.log
```

root で直接起動しない場合、スクリプトは `sudo` 経由で `tcpdump` を実行しようとします。

### 4. API の設定で生成ログを参照する

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

### 5. スクリプトを常駐させる

`systemd` サービス、`screen`、`tmux`、その他のプロセスマネージャーで常駐させる構成を推奨します。
API 側は生成されたログファイルを読むだけで、この補助スクリプト自体を起動する機能はありません。

## サーバーバージョン更新手順

この環境の Craftopia サーバーは Docker コンテナ `craftopia-server` と
イメージ `kagurazakanyaa/craftopia:latest` で動作していました。
今後は [compose.yaml](./compose.yaml) を使うと、更新を `docker compose pull && docker compose up -d`
で済ませられます。

### 初回のみ: Compose 化する

1. Compose ファイルをサーバー配置先へコピーする

```bash
mkdir -p /home/enirin/game-servers/craftopia
cp /path/to/Game-Server-Management-API/games/craftopia/compose.yaml \
  /home/enirin/game-servers/craftopia/compose.yaml
```

2. 必要なら環境変数テンプレートをコピーして値を調整する

```bash
cp /path/to/Game-Server-Management-API/games/craftopia/.env.sample \
  /home/enirin/game-servers/craftopia/.env
```

3. 既存コンテナを停止して、Compose 管理へ切り替える

```bash
docker stop craftopia-server
docker rm craftopia-server
cd /home/enirin/game-servers/craftopia
docker compose up -d
```

4. `docker compose ps` で起動を確認する

```bash
cd /home/enirin/game-servers/craftopia
docker compose ps
```

### 通常更新手順: pull && up -d

1. 念のためセーブデータを退避する

```bash
cp -a /home/enirin/game-servers/craftopia/data /home/enirin/game-servers/craftopia/data.backup-$(date +%F-%H%M%S)
```

2. Compose 管理ディレクトリへ移動する

```bash
cd /home/enirin/game-servers/craftopia
```

3. 最新イメージを取得して再作成する

```bash
docker compose pull && docker compose up -d
```

4. 起動ログを見て初期化完了を確認する

```bash
cd /home/enirin/game-servers/craftopia
docker compose logs -f craftopia
```

5. クライアント側も最新版へ更新してから再接続する

Compose ファイルは現在の `craftopia-server` の実設定をもとにしており、
`container_name: craftopia-server` のままなので API 側の設定変更は不要です。

### 補助手順: 起動時にゲーム本体更新も強制する

このイメージの `/docker-entrypoint.sh` には、環境変数 `FORCE_UPDATE=true` のとき
`steamcmd +app_update 1670340 validate` を実行する処理が入っています。
そのため、イメージ更新に加えて起動時のゲームデータ更新も強制したい場合は、
`.env` の `CRAFTOPIA_FORCE_UPDATE=true` にしてから通常更新手順を実行します。

```bash
cd /home/enirin/game-servers/craftopia
sed -i 's/^CRAFTOPIA_FORCE_UPDATE=.*/CRAFTOPIA_FORCE_UPDATE=true/' .env
docker compose pull && docker compose up -d
```

更新が終わったら、次回以降の起動で毎回 `steamcmd` を走らせないよう、`.env` を元に戻します。

```bash
cd /home/enirin/game-servers/craftopia
sed -i 's/^CRAFTOPIA_FORCE_UPDATE=.*/CRAFTOPIA_FORCE_UPDATE=false/' .env
docker compose up -d
```

### 更新後の確認ポイント

- `docker compose ps` で `craftopia-server` が `Up` になっていること
- `docker compose logs craftopia` に致命的なエラーが出ていないこと
- クライアント側も Steam で更新済みであること
- 接続できたあとに `presence_log_path` 側へ `LOGIN` が出ること

更新後も接続できない場合は、サーバーとクライアントのどちらかが別ビルドのままか、
あるいはコンテナ作り直し時に環境変数やポート設定を落としている可能性があります。
`docker compose config` と `docker inspect craftopia-server` の結果を比較すると切り分けしやすいです。

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