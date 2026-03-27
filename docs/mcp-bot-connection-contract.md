# Discord Bot 向け MCP 運用契約

## 目的

この文書は、Discord bot 側リポジトリが `Game-Server-Management-API` の MCP サーバーを利用する際の、確認フロー、会話運用、エラー再表現などのクライアント側運用契約を定義する。

MCP の純粋な interface 契約は [MCP Interface Specification](./mcp-interface-spec.md) を正本とし、本書は Discord bot 固有の責務だけを扱う。

## 参照順序

Discord bot 実装者は次の順で文書を参照する。

1. [MCP Interface Specification](./mcp-interface-spec.md)
2. 本書
3. 必要に応じてゲーム別保守文書

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

## IF 仕様の参照先

公開 tool と resource、入力と返却スキーマ、エラー契約は [MCP Interface Specification](./mcp-interface-spec.md) を参照する。

本書では、Discord bot 側で追加解釈が必要な運用ルールのみを定義する。

## 操作系 tool の扱い

次の tool は Discord bot 側で確認フロー必須とする。

- `start_server`
- `stop_server`

次の tool は通常の読み取りまたは管理操作として扱ってよい。

- `list_servers`
- `get_server_status`
- `get_server_maintenance_notes`
- `get_ip_player_name`
- `list_ip_player_names`
- `register_ip_player_name`

`register_ip_player_name` は書き込み系だが、サーバー起動停止と違って破壊的操作ではないため、必須確認対象には含めない。

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

## IP プレイヤー名マッピングの運用規約

Craftopia 向けの IP プレイヤー名マッピングは、Discord bot 側では次のように扱う。

### 目的

- 接続元 `IP:port` を人が識別しやすいプレイヤー名へ寄せる
- 未登録接続元の棚卸しをしやすくする

### bot 側推奨ユースケース

1. 管理者が `register_ip_player_name` を明示的に実行して登録する
2. 必要に応じて `get_ip_player_name` で単体確認する
3. 定期メンテナンスや問い合わせ時に `list_ip_player_names` で一覧確認する

### クライアント側の前提解釈

- `ip_address` は `IP` でも `IP:port` でも入力可能とみなしてよい
- server 側で正規化されるため、bot 側で port を除去する前処理は必須ではない
- 未登録時、Craftopia 通知表示は `IP` にフォールバックする
- port は通知表示に使われない

### UX 上の注意

- IP マッピング登録は server 起動停止ほど危険ではないが、入力ミスが起きやすい
- bot 側で登録結果の normalized IP をそのまま表示し、保存結果を明示するのが望ましい
- 未登録 IP を案内するときは、port を含めず IP のみを出す

## エラー再表現方針

error code 自体の契約は [MCP Interface Specification](./mcp-interface-spec.md) を参照する。

Discord bot 側推奨ハンドリング:

- `not_found`: 対象が見つからない旨を案内し、候補提示へ戻る
- `invalid_state`: すでに起動済みまたは停止済みとして案内する
- `runtime_unavailable`: 一時的障害として再試行方針を案内する
- `configuration_error`: 運用設定異常として管理者向けメッセージへ寄せる
- `internal_error`: 詳細を出しすぎず失敗として案内する

## 推奨会話フロー

### 読み取り系

1. ユーザーが状態照会または情報確認を依頼する
2. bot が適切な read tool を呼ぶ
3. bot が自然文に整形して返す

### 操作系

1. ユーザーが起動または停止を依頼する
2. bot が対象サーバーを確定する
3. bot が確認メッセージを返す
4. ユーザーが肯定したら operation tool を呼ぶ
5. bot が結果を返す

### IP プレイヤー名登録

1. 管理者が IP または IP:port とプレイヤー名の対応付けを依頼する
2. bot が `register_ip_player_name` を呼ぶ
3. bot が normalized IP と保存結果を返す

## 接続確認手順

bot 側の実装前に次を満たすこと。

1. `python mcp_server.py` で MCP サーバーが起動する
2. `http://127.0.0.1:8000/mcp` に `streamable HTTP` client で接続できる
3. `initialize` が成功する
4. `list_tools` で想定 tool が見える
5. [MCP Interface Specification](./mcp-interface-spec.md) に記載された必須 tool が利用可能である

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