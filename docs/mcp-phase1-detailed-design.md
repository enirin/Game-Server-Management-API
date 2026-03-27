# MCP Phase 1 詳細設計

## 目的

Phase 1 では、このリポジトリ内にゲームサーバー管理用の MCP サーバーを追加し、既存 Flask API と併存させる。

対象は最小限の問い合わせ・操作機能に絞る。

- サーバー一覧取得
- サーバー個別状態取得
- サーバー起動
- サーバー停止
- ゲーム別保守情報取得

本ドキュメントは、実装着手に必要なモジュール分割、公開契約、エラー契約、起動方式、テスト方針を定義する。

## 非目的

Phase 1 では次を行わない。

- `/tell` 通知の MCP 化
- Discord bot 側実装
- 任意コマンド実行やログ tail のような高権限ツール公開
- 認可の本格実装

## 現状整理

既存の責務は次のように分散している。

- [main.py](../main.py): Flask ルーティングと初期化
- [config_loader.py](../config_loader.py): 設定読み込みと正規化
- [server_runtime.py](../server_runtime.py): サーバー状態構築、起動、停止
- [log_watcher.py](../log_watcher.py): ログ追従と `/tell` 通知

現状の問題は、Flask API と MCP が同じユースケースを別々に持つとロジック重複しやすい点である。

したがって、Phase 1 では Flask ルートと MCP ツールの両方が呼ぶ共通サービス層を明示化する。

## 全体アーキテクチャ

```text
                +------------------------------+
                |        config_loader.py      |
                |   load_config / normalize    |
                +--------------+---------------+
                               |
                               v
                +------------------------------+
                |    management_service.py     |
                |   app use cases / errors     |
                +-----+------------------+-----+
                      |                  |
          REST        |                  |       MCP
                      v                  v
            +----------------+   +----------------+
            |    main.py     |   |  mcp_server.py |
            | Flask routes   |   | tools/resources|
            +----------------+   +----------------+
                      \                  /
                       \                /
                        v              v
                     +--------------------+
                     |  server_runtime.py  |
                     | status/start/stop   |
                     +--------------------+
```

## 新規追加モジュール

### 1. `management_service.py`

役割:

- 設定済みサーバー一覧の参照窓口
- Flask / MCP 共通のユースケース提供
- エラーの業務分類
- MCP / REST 返却のための共通データ整形

この層は HTTP も MCP も知らない。

### 2. `mcp_server.py`

役割:

- MCP server 初期化
- tool / resource 登録
- MCP 入出力と `management_service` の橋渡し
- 例外を MCP 向けエラーへ変換

### 3. `mcp_models.py`

役割:

- MCP で返す構造体の定義
- tool 引数、返却 payload、error payload の JSON schema 相当の定義補助

必須ではないが、スキーマを分離すると bot 側共有にも使いやすい。

## 既存モジュールの変更方針

### [main.py](../main.py)

現状:

- ルート内で `build_server_status`, `start_server_instance`, `stop_server_instance` を直接呼ぶ

変更後:

- `management_service` を初期化
- Flask ルートは `management_service` を呼ぶだけにする

### [server_runtime.py](../server_runtime.py)

現状:

- 実行ロジックと HTTP 向け payload 生成が混在

Phase 1 では大きく壊さず、まずは既存関数を `management_service` が利用する形にする。

将来候補:

- `start_server_instance` / `stop_server_instance` の HTTP 由来メッセージをドメイン結果へ寄せる
- `build_server_status` をより純粋な状態取得関数へ整理する

### [config_loader.py](../config_loader.py)

現状のまま利用する。

Phase 1 では `load_config()` の返却をそのまま `management_service` の入力に使う。

## 管理サービス層の設計

## 想定クラス

```python
class ManagementService:
    def __init__(self, servers: list[dict]):
        ...

    def list_servers(self) -> dict:
        ...

    def get_server_status(self, server_id: str) -> dict:
        ...

    def start_server(self, server_id: str) -> dict:
        ...

    def stop_server(self, server_id: str) -> dict:
        ...

    def get_server_maintenance_notes(self, server_id: str) -> dict:
        ...
```

## 想定例外

```python
class ManagementError(Exception):
    error_code: str
    message: str
    details: dict | None


class ServerNotFoundError(ManagementError):
    error_code = "not_found"


class RuntimeUnavailableError(ManagementError):
    error_code = "runtime_unavailable"


class InvalidServerStateError(ManagementError):
    error_code = "invalid_state"


class ConfigurationError(ManagementError):
    error_code = "configuration_error"
```

## 振る舞い

### `list_servers()`

- 全サーバーに対して [server_runtime.py](../server_runtime.py) の `build_server_status()` を呼ぶ
- 返却は既存 `/list` と整合する `{"servers": [...]}` を維持

### `get_server_status(server_id)`

- 単一サーバーに対して `build_server_status()` を呼ぶ
- 見つからなければ `ServerNotFoundError`
- 返却は `{"server": {...}}`

### `start_server(server_id)`

- 見つからなければ `ServerNotFoundError`
- 内部で `start_server_instance()` を呼ぶ
- 返却 payload は現行 API と近い構造を維持
- 非 2xx 相当は `ManagementError` 化してもよいが、Phase 1 では戻り値と status code の橋渡しでもよい

### `stop_server(server_id)`

- `start_server()` と同様

### `get_server_maintenance_notes(server_id)`

- `server_id` から `game` を解決
- 対応する `games/<game>/MAINTENANCE.md` を返す
- 見つからなければ `configuration_error` または `not_found`

## MCP サーバー設計

## Transport 方針

Phase 1 の実装は transport 差し替え可能な構造にする。

採用:

- Phase 1 は `streamable HTTP` を標準 transport とする
- `stdio` は将来のローカル検証用オプションに留める

本リポジトリ側では transport 抽象を持ち、サーバー登録処理とユースケース処理を分ける。

## ツール一覧

### 読み取り専用ツール

#### `list_servers`

引数なし。

返却:

```json
{
  "servers": [
    {
      "name": "craftopia",
      "server_aliases": ["くらふとぴあ"],
      "status": "online",
      "address": "60.70.94.179:6587",
      "stats": {
        "players": "0/8",
        "cpu": 12.5,
        "memory": 4.2
      },
      "day": 0
    }
  ]
}
```

#### `get_server_status`

入力:

```json
{
  "server_id": "craftopia"
}
```

返却:

```json
{
  "server": {
    "name": "craftopia",
    "server_aliases": ["くらふとぴあ"],
    "status": "online",
    "address": "60.70.94.179:6587",
    "stats": {
      "players": "0/8",
      "cpu": 12.5,
      "memory": 4.2
    },
    "day": 0
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

返却:

```json
{
  "server_id": "craftopia",
  "game": "craftopia",
  "path": "games/craftopia/MAINTENANCE.md",
  "content": "..."
}
```

### 操作ツール

#### `start_server`

入力:

```json
{
  "server_id": "craftopia"
}
```

返却:

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

返却:

```json
{
  "success": true,
  "message": "Server 'craftopia' is stopping...",
  "server_name": "craftopia"
}
```

## Resource 一覧

### `servers://catalog`

全サーバーの静的構成寄り情報を返す。

用途:

- bot 側で対象候補を提示する
- エージェントに `server_id`, `aliases`, `game`, `runtime` を見せる

### `servers://status`

`list_servers()` と同等の現在状態を返す。

### `servers://status/{server_id}`

単一サーバーの状態を返す。

### `games://maintenance/{game}`

ゲーム別の保守情報を返す。

## エラー契約

MCP ツールは最低限次のエラーコードを返せるようにする。

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

候補コード:

- `not_found`
- `invalid_state`
- `runtime_unavailable`
- `configuration_error`
- `internal_error`

REST と MCP の差異を減らすため、メッセージ文面はできる限り既存 API に寄せる。

## 依存ライブラリ方針

Phase 1 では MCP サーバー実装用ライブラリを `requirements.txt` に追加する。

採用条件:

- Python 3.10+ 対応
- tool / resource を素直に公開できる
- `stdio` または HTTP transport に対応できる
- 実装が薄く保てる

ライブラリ候補の最終決定は実装開始時に行うが、詳細設計としては `mcp_server.py` が外部ライブラリに依存しすぎない構造を優先する。

## Flask API との整合方針

Phase 1 では既存 API 契約を壊さない。

方針:

- Flask ルートは `management_service` を呼ぶだけに寄せる
- 返却 JSON は既存 [api_contract.md](../api_contract.md) と整合する
- 新機能の追加は原則 MCP 側で行い、REST 側は後から必要に応じて追従する

## 起動構成

## 最小構成

- `main.py`: Flask API 起動
- `mcp_server.py`: MCP サーバー起動

Phase 1 では次のいずれかを選ぶ。

1. 別エントリポイントで別プロセス起動
2. 単一プロセスで両方起動

推奨は 1。理由は次のとおり。

- 既存 API 側の安定性に影響しにくい
- Discord bot 側との接続方式を変えやすい
- ローカル実行時の切り分けがしやすい

## 推奨エントリポイント

- `python main.py`
- `python mcp_server.py`

## テスト方針

### 単体テスト

- `ManagementService.list_servers()`
- `ManagementService.get_server_status()`
- `ManagementService.start_server()`
- `ManagementService.stop_server()`
- `ManagementService.get_server_maintenance_notes()`
- エラー変換

### 契約テスト

- MCP tool の引数スキーマ
- MCP tool の返却スキーマ
- 主要 error code の整合

### 回帰テスト

- Flask `/list`
- Flask `/start/<server_name>`
- Flask `/stop/<server_name>`

## 実装順序

1. `management_service.py` を追加する
2. `main.py` を `management_service` 経由へ切り替える
3. `mcp_server.py` を追加して最小ツールを公開する
4. `get_server_maintenance_notes` を追加する
5. エラー契約を整える
6. テストを追加する
7. README と連携資料を更新する

## bot 側へ最初に共有する項目

Phase 1 完了時点で、Discord bot 側へ少なくとも次を共有する。

- 使用する MCP transport
- ツール名
- 入力 JSON 例
- 返却 JSON 例
- エラーコード一覧
- 操作ツールは確認必須というルール

## 受け入れ条件

- MCP から `list_servers` と `get_server_status` が呼べる
- MCP から `start_server` と `stop_server` が呼べる
- 保守情報を MCP resource または tool 経由で参照できる
- Flask API 既存挙動が維持される
- bot 側へ渡せる最小契約が文書化されている