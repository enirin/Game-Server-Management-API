# Discordを利用したゲームサーバ管理システム構築例

このドキュメントは、以下2つのアプリケーションを組み合わせて、
**Discordチャンネル上の自然な会話でゲームサーバーを管理する仕組み**を構築するための説明資料です。

- ゲームサーバ管理API: `Game-Server-Management-API`（本リポジトリ）
- Discord Bot（AI対話 + 外部通知受付）: https://github.com/enirin/discord-bot

## 1. コンセプト

通常のサーバ管理は「SSHログインしてコマンド実行」が中心ですが、本構成では次を実現します。

- Discord上でユーザーが自然言語で依頼
- Discord Botが意図を解釈して管理APIを呼び出し
- ゲームサーバの起動/停止/状態確認を実行
- ゲームサーバ側ログイン/ログアウトイベントを管理APIが検知
- 管理APIからDiscord Botの `/tell` に通知し、Botが自然な文面でチャンネル投稿

結果として、**運用操作の入口をDiscordに一本化**できます。

## 2. システム構成

```text
[Discord Users]
     |
     v
[Discord Channel]
     |
     v
[discord-bot]
  - AI対話
  - /tell 受付
  - 管理API呼び出し
     |
     v
[Game-Server-Management-API]
  - /list /start /stop
  - docker/native 両対応
  - ログ監視とイベント抽出
     |
     +--> [Valheim (Docker)]
     +--> [7 Days to Die (Native Linux)]
```

## 3. 各コンポーネントの役割

### 3.1 Discord Bot (`discord-bot`)

- Discordチャンネルでの自然な会話を受け付け
- ユーザーの意図をもとに管理APIを呼び出し
- `POST /tell` を受け、AI応答を生成して指定チャンネルへ投稿

### 3.2 Game-Server-Management-API

- `GET /list`: サーバ一覧・状態を返却
- `POST /start/{server_name}`: サーバ起動
- `POST /stop/{server_name}`: サーバ停止
- 各サーバログをリアルタイム監視し、ログイン/ログアウトを検知
- 検知イベントを Discord Bot の `/tell` に送信

## 4. `/tell` 連携のポイント

管理APIはログ解析イベント発生時に、Discord Botへ以下形式で通知します。

- `prompt`: Botに渡すシステム通知文
- `channel_id` (任意): 投稿先チャンネルID（server_idごとに指定可能）
- `X-Send-Token` (任意): Bot側で `web_endpoint_token` 設定時に必要

例（手動テスト）:

```bash
curl -X POST "http://127.0.0.1:5050/tell" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"システム通知: valheim でプレイヤー Alice がログインしました。", "channel_id":123456789012345678}'
```

## 5. この構成で得られる価値

- 管理操作の簡略化: Discord上で完結
- 通知品質の向上: Botが自然文で案内
- 運用負荷の軽減: ログ監視と通知を自動化
- 将来拡張が容易: ゲーム追加時はログパーサ追加で対応可能

## 6. 導入手順（概要）

1. Discord Bot をセットアップして起動
2. Game-Server-Management-API をセットアップして起動
3. API側 `config.yaml` で次を設定
   - `discord.tell_url`
   - `discord.web_endpoint_token`（必要時）
   - `servers`（`runtime: docker/native`、`game`、`channel_id` など）
4. Discordから管理コマンド相当の発話で動作確認
5. ゲームサーバログイン/ログアウト時に `/tell` 通知が投稿されることを確認

## 7. 設定例（管理API側）

```yaml
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
    log_file_path: /opt/7d2d/Logs/current.log
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
    channel_id: 123456789012345678
```

## 8. 運用時の注意

- `web_endpoint_token` を使う場合、Bot側設定と完全一致させる
- `channel_id` を省略した場合、Bot側デフォルト送信先に投稿される
- native運用では `log_file_path` のローテーション運用（切替タイミング）を考慮する
- Docker運用では API実行ユーザーの Docker 権限を確認する

## 9. 代表的な利用シナリオ

- プレイヤー: 「今 valheim サーバー動いてる？」
- Bot: 管理APIの `/list` を参照して回答
- 管理者: 「7d2d サーバー起動して」
- Bot: `/start/7d2d` 実行、結果を返信
- プレイヤーがゲームへログイン
- 管理API: ログイベント検知 -> `/tell`
- Bot: 自然な歓迎メッセージをDiscordへ投稿

## 10. まとめ

この構成により、

- **会話型インターフェース（Discord Bot）**
- **実行基盤制御（Game-Server-Management-API）**
- **イベント通知（/tell）**

を組み合わせた、実運用しやすいゲームサーバ管理システムを構築できます。
