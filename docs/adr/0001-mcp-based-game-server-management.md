# ADR 0001: ゲームサーバー管理機能の MCP 化

## ステータス

承認済み

## 日付

2026-03-27

## 背景

現在の構成では、Discord bot が `Game-Server-Management-API` の Flask API を直接呼び出して、ゲームサーバーの状態確認や起動・停止を行っています。

現状の責務は大きく次の 2 つに分かれています。

- 問い合わせと操作: `GET /list`, `POST /start/{server_name}`, `POST /stop/{server_name}`
- イベント通知: 管理サービスから Discord bot の `/tell` への push 通知

この構成でも動作はしますが、AI エージェント機能を保守しやすく整理するには、Discord bot 側が HTTP API の詳細を直接知るよりも、エージェント向けに整理されたインターフェースを経由する方が望ましいです。

## 決定

ゲームサーバー管理サービスは、既存 Flask API と併存する形で MCP サーバー機能を提供する。

Discord bot 側は、ゲームサーバー管理 MCP サーバーを利用する MCP ホストとして実装する。

初期段階では、イベント通知の仕組みは MCP へ寄せず、従来どおり `/tell` による push 通知を維持する。

## 採用理由

- AI エージェント向けの問い合わせ・操作境界を MCP として整理できる
- Discord bot 側が API エンドポイントや返却仕様の細部を直接抱えなくてよくなる
- 将来、Discord 以外のクライアントや別のエージェント実行基盤にも再利用しやすい
- 既存 REST API を即時廃止せず、段階的に移行できる

## 採用しない案

### 1. 既存 Flask API をそのまま使い続ける

短期的な変更量は最小ですが、AI エージェント向けの責務整理や他クライアントへの再利用性は改善しません。

### 2. Discord bot 側だけで独自ツール層を作る

Bot 側の都合に最適化しすぎるため、管理サービスの機能契約が bot 実装に埋め込まれやすくなります。

### 3. イベント通知まで含めて全面的に MCP 化する

初期段階では責務の切り分けが複雑になりやすく、既存 `/tell` で十分に機能している push 通知まで巻き込む必要性が低いため採用しません。

## スコープ

この ADR が対象とするのは次です。

- サーバー一覧取得
- サーバー個別状態取得
- サーバー起動
- サーバー停止
- ゲーム別保守情報の参照

この ADR の対象外は次です。

- `/tell` によるイベント通知の置き換え
- Discord サーバー上の権限管理実装の完了
- ログ tail や任意コマンド実行のような高権限操作の一般公開

## 操作権限ポリシー

初期方針は次のとおりです。

- 読み取り専用ツールと操作ツールは分離する
- `start_server` と `stop_server` は確認必須とする
- 初期実装では、Discord bot 利用者は誰でも操作要求を出せる前提でよい
- 将来的には Discord サーバーの管理ロール保有を操作条件にできるよう拡張可能な設計にする

このため、MCP のツール設計でも次の 2 群に分ける。

- 読み取り専用: `list_servers`, `get_server_status`, `get_server_maintenance_notes`
- 操作用: `start_server`, `stop_server`

## MCP サーバー側の方針

### 提供形態

- 既存 Flask API と併存する
- 内部では既存 runtime ロジックを再利用する
- REST と MCP の両方から同一サービス層を呼ぶ構成に寄せる

### 初期ツール候補

- `list_servers()`
- `get_server_status(server_id)`
- `start_server(server_id)`
- `stop_server(server_id)`
- `get_server_maintenance_notes(server_id)`

### 初期リソース候補

- `servers://catalog`
- `servers://status`
- `servers://status/{server_id}`
- `games://maintenance/{game}`

### 返却方針

- 返却データは自然文より構造化情報を優先する
- 可能な限り既存 API 契約のフィールド名を維持する
- エラーは `not_found`, `invalid_state`, `runtime_unavailable` などの分類を持たせる
- `start` / `stop` は idempotent に扱う

## Discord bot 側の方針

Discord bot 側は、ゲームサーバー管理機能専用の単純クライアントではなく、MCP ホストとして実装する。

理由は次のとおりです。

- 将来、ゲーム管理以外の MCP サーバーも接続できるようにするため
- AI エージェントに対して複数の MCP ツールセットを統一的に提供できるため
- bot 側の実装を特定サービス専用に固定しないため

### bot 側で守るべき運用ルール

- 読み取り専用ツールは自動実行可
- `start_server` / `stop_server` は確認プロンプトを挟んでから実行する
- `/tell` による push 通知は当面維持する
- 将来のロール制御を前提に、実行者情報を操作ハンドラまで伝播できる設計にする

## 影響範囲

### このリポジトリ

- MCP サーバー実装の追加
- 既存 Flask ルートが使う共通サービス層の明確化
- ドキュメント更新

### Discord bot 側リポジトリ

- MCP ホスト実装の追加
- エージェントへのツール公開設定
- 確認フロー付きの操作実装
- 将来のロール制御を見据えた実行コンテキスト受け渡し

## 段階的移行方針

1. 管理サービス側に MCP サーバーを追加する
2. `list/start/stop/get status` の最小ツールを公開する
3. Discord bot 側に MCP ホストを実装する
4. 読み取り系から順に REST 呼び出しを MCP へ置き換える
5. 操作系を確認付きで MCP へ移行する
6. 保守情報や補助ツールを追加する

## 成功条件

- Discord bot 側 AI エージェントが MCP 経由でサーバー状態を取得できる
- `start_server` / `stop_server` が確認付きで実行できる
- `/tell` 通知は既存どおり機能する
- REST API は移行期間中も後方互換を維持する

## 未決事項

- MCP の transport を `stdio` と `streamable HTTP` のどちらで始めるか
- Discord bot 側の確認 UX をどう実装するか
- 管理ロール判定を bot 側だけで持つか、管理サービス側へも伝えるか
- 将来的に `/tell` を MCP イベントへ寄せるかどうか