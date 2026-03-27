# MCP IF 仕様

## 目的

この文書は、`Game-Server-Management-API` が公開する Model Context Protocol の interface を定義する。

これは MCP client 向けの、人が読むための正本 IF 契約である。transport、tool と resource の公開面、payload 形状、互換性の前提を扱う。Discord の確認フローや UX 文言のような client 固有の振る舞いは意図的にスコープ外とする。

## スコープ

この仕様では次を定義する。

- transport と endpoint の前提
- 公開する MCP tool
- 公開する MCP resource
- 応答 payload と error 形状の期待値
- 互換性と変更管理のルール

この仕様では次を定義しない。

- Discord bot の会話フロー
- 確認 UI や対話文言
- client 側の role ベース認可ポリシー
- 内部 agent planner の実装方針

## Transport

- transport: `streamable HTTP`
- server 実装: [mcp_server.py](../mcp_server.py)
- 既定 endpoint: `http://127.0.0.1:8000/mcp`

接続先を制御する既定の環境変数:

- `MCP_HOST`
- `MCP_PORT`
- `MCP_PATH`
- `MCP_JSON_RESPONSE`
- `MCP_STATELESS_HTTP`
- `GAME_SERVER_CONFIG_PATH`

関連する運用パラメータ:

- `GAME_SERVER_IP_PLAYER_MAP_PATH`: IP とプレイヤー名のマッピング tool が使う永続ファイルパスを上書きする

## Discovery

client は MCP の initialize と tool または resource discovery を、現在利用可能な interface の機械可読な正本として扱うこと。

この文書は、その discovery で見える公開面について、意図した使い方と安定性の前提を説明する人間向け契約である。

## Tools

### 読み取り系 tool

#### `list_servers`

入力なし。

成功時の返却例:

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

意味:

- 管理対象サーバー全件の現在状態を返す
- 一覧表示や server_id の曖昧性解消に使う

#### `get_server_status`

入力:

```json
{
  "server_id": "craftopia"
}
```

成功時の返却例:

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

意味:

- 指定した管理対象サーバー 1 件の現在状態を返す

#### `get_server_maintenance_notes`

入力:

```json
{
  "server_id": "craftopia"
}
```

成功時の返却例:

```json
{
  "server_id": "craftopia",
  "game": "craftopia",
  "path": "games/craftopia/MAINTENANCE.md",
  "content": "..."
}
```

意味:

- 対象サーバーのゲームに対応する保守文書を返す

#### `get_ip_player_name`

入力:

```json
{
  "ip_address": "203.0.113.10"
}
```

成功時の返却例:

```json
{
  "ip_address": "203.0.113.10",
  "player_name": "Alice",
  "found": true
}
```

意味:

- 指定した IP アドレスに登録済みのプレイヤー名があれば返す
- `found` が `false` の場合、`player_name` は `null` になる
- 入力は `IP` でも `IP:port` でもよく、server 側で `IP` に正規化する

#### `list_ip_player_names`

入力なし。

成功時の返却例:

```json
{
  "path": "ip_player_map.txt",
  "mappings": [
    {
      "ip_address": "203.0.113.10",
      "player_name": "Alice"
    }
  ]
}
```

意味:

- 現在の永続 IP とプレイヤー名のマッピング一覧を返す
- `path` は API workspace の base directory からの相対パスを返す

### 書き込み系 tool

#### `register_ip_player_name`

入力:

```json
{
  "ip_address": "203.0.113.10:54000",
  "player_name": "Alice"
}
```

成功時の返却例:

```json
{
  "ip_address": "203.0.113.10",
  "player_name": "Alice",
  "path": "ip_player_map.txt"
}
```

意味:

- 正規化した IP に対する永続マッピングを新規登録または更新する
- 入力は `IP` でも `IP:port` でもよい
- 保存される key は常に port を除いた正規化済み IP である
- Craftopia の在席通知は、生の IP 表示へフォールバックする前にこのマッピングを参照する

#### `start_server`

入力:

```json
{
  "server_id": "craftopia"
}
```

成功時の返却例:

```json
{
  "success": true,
  "message": "Server 'craftopia' is starting...",
  "server_name": "craftopia"
}
```

意味:

- 管理対象サーバーの起動を要求する
- 実行前の確認フローは client 側で制御する前提とする

#### `stop_server`

入力:

```json
{
  "server_id": "craftopia"
}
```

成功時の返却例:

```json
{
  "success": true,
  "message": "Server 'craftopia' is stopping...",
  "server_name": "craftopia"
}
```

意味:

- 管理対象サーバーの停止を要求する
- 実行前の確認フローは client 側で制御する前提とする

## Resources

### `servers://catalog`

- 静的寄りのサーバーカタログを返す

### `servers://status`

- 全サーバーの現在状態を返す

### `servers://status/{server_id}`

- 指定したサーバーの現在状態を返す

### `games://maintenance/{game}`

- 指定したゲームの保守メモを返す

## Payload 規約

### ServerStatus

status payload は、REST API で使っているものと同じ論理構造に従う。

- `name`: サーバー識別子
- `server_aliases`: ユーザー向け別名一覧
- `status`: `online`、`offline`、`busy` のいずれか
- `address`: ユーザー向け接続先表示
- `stats.players`: 現在人数と最大人数。形式は `1/8` のような文字列
- `stats.cpu`: 正規化済み CPU 使用率
- `stats.memory`: メモリ使用量 GB
- `day`: 取得できたゲーム内日数。取得不可なら `0`

### Craftopia の IP マッピング挙動

- Craftopia の在席イベントで入ってくる接続元は `IP:port` から `IP` へ正規化する
- マッピングが存在する場合、通知には登録済みプレイヤー名を使う
- マッピングが存在しない場合、通知には正規化済み IP を使う
- 通知には port 番号を出さない

## Error 契約

tool が失敗したとき、server は少なくとも次の形を返す。

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

公開する error code:

- `not_found`
- `invalid_state`
- `runtime_unavailable`
- `configuration_error`
- `internal_error`

追加の validation 失敗は、domain error 階層の外で送出された場合、現状では説明付きの `internal_error` として表面化する場合がある。

## 互換性ポリシー

次は後方互換を保つ変更として扱う。

- 新しい tool の追加
- 新しい resource の追加
- 成功 payload への任意 field の追加
- 説明文の追加や拡充

次は client 側との明示的な調整を必要とする。

- tool の削除または改名
- 必須入力 field の変更
- 応答 field の意味変更
- 公開済み error code の削除

## バージョン管理と変更管理

現時点では、このリポジトリは MCP 専用の独立した semantic version を公開していない。

この方針が変わるまでは、interface 変更時にこの文書と、bot 向け運用契約である [mcp-bot-connection-contract.md](./mcp-bot-connection-contract.md) をセットで更新して通知すること。