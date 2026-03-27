# Discord Bot 向け MCP 接続契約

## 目的

この文書は、Discord bot 側リポジトリが `Game-Server-Management-API` の MCP サーバーへ接続し、読み取り系と操作系のゲームサーバー管理機能を利用するための実装契約を定義する。

対象読者は Discord bot 側の実装担当者であり、設計議論ではなく接続と運用の具体を共有することを目的とする。

## 接続前提

- transport は `streamable HTTP` を使う
- MCP サーバーは本リポジトリの [mcp_server.py](../mcp_server.py) で起動する
- Flask API とは別プロセスで動かす
- 初期段階では認証なしのローカル接続を前提とする
- 操作系 tool は bot 側で確認フローを必須にする

## 接続先

既定値:

- URL: `http://127.0.0.1:8000/mcp`
- Method: `POST` と `GET`
- Transport: `streamable HTTP`

起動時に変更可能な環境変数:

- `MCP_HOST`
- `MCP_PORT`
- `MCP_PATH`
- `MCP_JSON_RESPONSE`
- `MCP_STATELESS_HTTP`
- `GAME_SERVER_CONFIG_PATH`

bot 側では、接続先 URL を設定値として外出しできるようにすること。

## 推奨接続設定

初期推奨値は次のとおり。

- URL: `http://127.0.0.1:8000/mcp`
- `json_response`: 有効
- `stateless_http`: 有効

理由:

- bot 側を別ホストへ逃がしやすい
- HTTP ベースで疎通確認しやすい
- stateful session を前提にしないため運用が単純

## bot 側の責務

bot 側は MCP host として次を担う。

- MCP サーバーへの接続確立
- 初期化と tool/resource discovery
- 読み取り系 tool の自動実行
- 操作系 tool 実行前の確認
- エラーコードに応じたユーザー向け再表現
- 将来の権限制御を差し込める構造の維持

このリポジトリ側は、権限判定や確認 UI を提供しない。

## 公開 tool 一覧

### 読み取り系

#### `list_servers`

入力なし。

返却例:

```json
{
  "servers": [
    {
      "name": "craftopia",
      "server_aliases": ["くらふとぴあ", "クラフトピア"],
      "status": "online",
      "address": "60.70.94.179:6587",
      "stats": {
        "players": "1/8",
        "cpu": 18.9,
        "memory": 6.1
      },
      "day": 293
    }
  ]
}
```

利用目的:

- 一覧表示
- 自然言語問い合わせへの候補抽出
- server_id の曖昧性解消

#### `get_server_status`

入力:

```json
{
  "server_id": "craftopia"
}
```

返却例:

```json
{
  "server": {
    "name": "craftopia",
    "server_aliases": ["くらふとぴあ", "クラフトピア"],
    "status": "online",
    "address": "60.70.94.179:6587",
    "stats": {
      "players": "1/8",
      "cpu": 18.9,
      "memory": 6.1
    },
    "day": 293
  }
}
```

#### `get_server_maintenance_notes`

入力:

```json
{
  "server_id": "craftopia"
}
```

返却例:

```json
{
  "server_id": "craftopia",
  "game": "craftopia",
  "path": "games/craftopia/MAINTENANCE.md",
  "content": "..."
}
```

利用目的:

- エージェントにゲーム固有の保守手順を読ませる
- 障害対応時に参照させる

### 操作系

#### `start_server`

入力:

```json
{
  "server_id": "craftopia"
}
```

成功例:

```json
{
  "success": true,
  "message": "Server 'craftopia' is starting...",
  "server_name": "craftopia"
}
```

#### `stop_server`

入力:

```json
{
  "server_id": "craftopia"
}
```

成功例:

```json
{
  "success": true,
  "message": "Server 'craftopia' is stopping...",
  "server_name": "craftopia"
}
```

## 公開 resource 一覧

### `servers://catalog`

静的寄りのサーバーカタログを返す。

### `servers://status`

全サーバーの現在状態を返す。

### `servers://status/{server_id}`

単一サーバーの現在状態を返す。

### `games://maintenance/{game}`

ゲーム別保守情報を返す。

## エラー契約

tool の失敗時は、少なくとも次の形式を返す。

```json
{
  "error": {
    "code": "not_found",
    "message": "Server 'foo' not found",
    "details": {
      "server_id": "foo"
    }
  }
}
```

利用する error code:

- `not_found`
- `invalid_state`
- `runtime_unavailable`
- `configuration_error`
- `internal_error`

bot 側推奨ハンドリング:

- `not_found`: 対象サーバーが見つからない旨を案内し、候補提示へ戻る
- `invalid_state`: すでに起動済み / 停止済みとして案内する
- `runtime_unavailable`: 一時的障害として再試行方針を案内する
- `configuration_error`: 運用設定異常として管理者向けメッセージへ寄せる
- `internal_error`: 詳細を出しすぎず失敗として案内する

## 確認フロー契約

`start_server` と `stop_server` は bot 側で確認を必須とする。

### 必須要件

1. ユーザーの依頼直後に operation tool を実行しない
2. 対象サーバー名と操作内容を明示して確認を返す
3. 明示的な肯定応答があった場合のみ tool を呼ぶ
4. 否定応答またはタイムアウト時は tool を呼ばない
5. 実行後は MCP の返却 `message` を含めて結果を返す

### 推奨確認文面

起動:

- 「`craftopia` を起動します。実行しますか？」

停止:

- 「`craftopia` を停止します。実行しますか？」

### 推奨肯定応答

- 「はい」
- 「実行して」
- 「お願いします」
- ボタン操作による確認

### 推奨否定応答

- 「いいえ」
- 「やめて」
- キャンセルボタン

### 確認状態の保持

bot 側は少なくとも次を pending 操作として保持できること。

- `operation`: `start_server` または `stop_server`
- `server_id`
- `requested_by`
- `channel_id`
- `requested_at`
- `expires_at`

### タイムアウト方針

推奨:

- 30 秒から 120 秒の範囲で設定
- タイムアウト後は pending 操作を破棄
- 再度依頼してくださいと案内する

## 推奨会話フロー

### 読み取り系

1. ユーザーが状態照会を依頼
2. bot が `list_servers` または `get_server_status` を呼ぶ
3. bot が自然文に整形して返す

### 操作系

1. ユーザーが起動または停止を依頼
2. bot が対象サーバーを確定する
3. bot が確認メッセージを返す
4. ユーザーが肯定したら operation tool を呼ぶ
5. bot が結果を返す

## 接続確認手順

bot 側の実装前に次を満たすこと。

1. `python mcp_server.py` で MCP サーバーが起動する
2. `http://127.0.0.1:8000/mcp` に `streamable HTTP` client で接続できる
3. `initialize` が成功する
4. `list_tools` で想定 tool が見える
5. `list_servers` が成功する

このリポジトリでは上記 1 から 5 の疎通確認済み。

## 非スコープ

この契約書では次を定義しない。

- Discord 側の UI 詳細
- bot 内部の agent planner 実装
- Discord role ベース認可の最終仕様
- `/tell` 通知の MCP 置き換え

## 今後の拡張ポイント

- 実行者情報の server 側伝播
- 認可情報の受け渡し
- 操作履歴の監査
- `games://maintenance/{game}` の bot 側活用強化
- 追加 tool の段階公開