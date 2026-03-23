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
- `extract_day()` は未オーバーライドです。Craftopia では現時点でゲーム内日数の抽出に対応していません。

## 運用上の注意

- Docker 管理の Craftopia でも、コンテナの online / offline 状態や CPU / メモリ使用量は Docker 側から取得します。
- リアルタイム通知と現在人数の推定は、`servers[].presence_log_path` に指定したログファイルを使います。
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
```

### 5. スクリプトを常駐させる

`systemd` サービス、`screen`、`tmux`、その他のプロセスマネージャーで常駐させる構成を推奨します。
API 側は生成されたログファイルを読むだけで、この補助スクリプト自体を起動する機能はありません。

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
```