# MCP 移行計画

## 目的

`Game-Server-Management-API` が提供するゲームサーバー管理機能を MCP サーバーとして公開し、Discord bot 側の AI エージェント機能を、より保守しやすい責務分離で再構成する。

本計画は、別リポジトリで作業する Discord bot 側との連携前提で、作業順序、受け渡し事項、確認ポイントを整理するためのものです。

## 前提となる決定事項

詳細は [ADR 0001](./adr/0001-mcp-based-game-server-management.md) を参照。

Phase 1 の詳細設計は [MCP Phase 1 詳細設計](./mcp-phase1-detailed-design.md) を参照。

MCP の interface 契約は [MCP Interface Specification](./mcp-interface-spec.md) を参照。

Discord bot 実装担当者向けの運用契約は [Discord Bot 向け MCP 運用契約](./mcp-bot-connection-contract.md) を参照。

- 管理サービス側は Flask API と MCP サーバーを併存させる
- Discord bot 側は MCP ホストとして実装する
- `/tell` 通知は初期段階では維持する
- 読み取り専用ツールと操作ツールを分離する
- `start_server` / `stop_server` は確認必須
- 初期段階では誰でも操作要求できる前提でよい
- 将来的に Discord の管理ロール条件を追加できるようにする

## フェーズ構成

## 進捗状況

- Phase 0: 完了
- Phase 1: 完了
- Phase 2: 完了
- Phase 3: 完了

## Phase 0: 境界整理

### このリポジトリで行うこと

- MCP に出す機能を最小セットに絞る
- REST API と MCP が共有するサービス層を切り出す方針を確定する
- エラー分類と返却スキーマ方針を決める

### Discord bot 側へ連携すること

- 読み取り系と操作系のツール一覧
- 操作系は確認必須というルール
- `/tell` は残すという境界定義

### 完了条件

- ADR が承認済みである
- 初期ツール一覧が確定している

## Phase 1: 管理サービス側に MCP サーバーを追加

### 実装対象

- MCP サーバー本体
- 共通サービス層
- 初期ツール 4 個と保守情報参照

### 初期ツール

- `list_servers`
- `get_server_status`
- `start_server`
- `stop_server`
- `get_server_maintenance_notes`

### 初期リソース

- `servers://catalog`
- `servers://status`
- `servers://status/{server_id}`
- `games://maintenance/{game}`

### このリポジトリ内の想定変更箇所

- [main.py](../main.py)
- [server_runtime.py](../server_runtime.py)
- [config_loader.py](../config_loader.py)
- 新規: `mcp_server.py`
- 新規: `management_service.py` または同等の共通層

### 完了条件

- MCP 経由で状態取得と起動停止が呼べる
- 既存 REST API は壊れていない

## Phase 2: Discord bot 側に MCP ホストを追加完了

Discord bot 側の実装は `enirin/discord-bot` に反映済み。

### bot 側で実装できた内容

- `streamable HTTP` で MCP サーバーへ接続する MCP client を追加
- 起動時に `initialize` / `list_tools` / `list_resources` / `list_resource_templates` を実行し、公開 interface を検証
- 読み取り系 tool を bot コマンドと AI エージェントの双方から利用可能にした
- `start_server` / `stop_server` を pending 操作として保持し、確認後にのみ実行するフローを追加
- 確認待ち操作の `confirm` / `cancel` / timeout を実装
- 実行者情報とチャンネル情報を保持し、将来の権限制御を差し込める構造を用意

### このリポジトリから bot 側へ渡した情報

- MCP ツール一覧
- 引数仕様
- 返却スキーマ
- エラー分類
- 推奨確認文面のたたき台
- 接続 URL と transport の既定値

### 完了条件

- bot 側 AI エージェントが MCP で状態照会できる
- bot 側から確認付きで起動停止できる
- 上記 2 点は Discord bot 側で達成済み

## Phase 3: 移行と運用安定化

現状確認では、Phase 3 の完了条件は満たせていると判断する。

### 進捗再確認

#### API 側

- 完了: `get_server_maintenance_notes` tool と `games://maintenance/{game}` resource を公開済み
- 完了: `servers://catalog` / `servers://status` / `servers://status/{server_id}` を公開済み
- 完了: 共通サービス層でエラー分類と保守情報解決を実装済み
- 完了: 保守情報参照のテストを追加済み
- 完了: MCP 接続契約と移行計画の文書化を実施済み
- 完了: 追加の説明用 prompt / helper は現時点では不要と判断済み
- フォローアップ候補: MCP 利用を前提にした運用手順の追記

#### bot 側

- 完了: `list_servers` / `get_server_status` / `get_server_maintenance_notes` を MCP 経由で利用済み
- 完了: `start_server` / `stop_server` を確認付きで MCP 経由実行済み
- 完了: bot 起動時の discovery と公開 interface 検証を実装済み
- 完了: 自然言語とコマンドの双方から同じ MCP ベースの skill を利用済み
- 完了: `/tell` 通知フローは維持済み
- 完了: catalog 再取得用の Web API は MCP の `list_servers` を使う構成に移行済み
- フォローアップ候補: 旧 REST クライアントや旧仕様書の整理
- フォローアップ候補: 実運用で必要になった権限制御ポリシーの具体化

### このリポジトリで行うこと

- 保守情報を MCP resource として参照可能にする
- 必要なら MCP 利用者向けの補助 artifact を追加する
- ドキュメント更新

ここでいう「説明用 prompt / helper」は、MCP tool そのものではなく、LLM や bot 実装がゲーム管理 MCP を使いやすくするための補助情報を指していた。たとえば次のようなものを想定していた。

- どの tool をどの順で使うかを説明する system prompt 断片
- 操作系 tool は確認必須であることを毎回守らせるための helper 文面
- 障害対応時に `games://maintenance/{game}` を先に読むよう促す補助ガイド

ただし現状は、Discord bot 側が独自の skill 層、確認フロー、保守情報参照導線をすでに持っている。そのため、このリポジトリ側で別途 prompt / helper を配布しなくても運用できると判断する。

### Discord bot 側で行うこと

- 既存 REST 呼び出しのうち読み取り系を MCP へ置換
- 問題なければ操作系も MCP へ移行
- `/tell` はそのまま維持

### 完了条件

- bot 側の主要なサーバー管理機能が MCP ベースへ移行済み
- 既存通知フローは維持されている

上記 2 点を満たしているため、Phase 3 は完了とする。

### API 側完了確認チェックリスト

- [x] `get_server_maintenance_notes` tool を公開する
- [x] `games://maintenance/{game}` resource を公開する
- [x] `servers://catalog` / `servers://status` / `servers://status/{server_id}` を公開する
- [x] MCP tool と REST API が同じサービス層を参照する構成にする
- [x] MCP 向けエラー分類を `not_found` / `invalid_state` / `runtime_unavailable` / `configuration_error` / `internal_error` で揃える
- [x] 保守情報参照のテストを追加する
- [x] bot 側実装に必要な接続契約と移行計画を文書化する
- [x] bot 側で実際に必要だった返却値とエラー分類を契約文書へ反映する
- [x] 説明用 prompt / helper は現状不要と判断し、その意図を文書へ明記する
- [x] Phase 3 完了時点の運用前提を移行計画へ反映する

### bot 側完了確認チェックリスト

- [x] MCP 接続先 URL を設定値として外出しする
- [x] 起動時に `initialize` / discovery を実行し、公開 tool と resource を検証する
- [x] `list_servers` を MCP 経由で呼ぶ
- [x] `get_server_status` を MCP 経由で呼ぶ
- [x] `get_server_maintenance_notes` を MCP 経由で呼ぶ
- [x] `start_server` / `stop_server` を確認付きで MCP 経由実行する
- [x] 自然言語経由のゲームサーバー操作を MCP ベースへ移行する
- [x] catalog 再取得系の内部 Web API を MCP ベースへ移行する
- [x] `/tell` 通知フローを維持する
- [x] 主要なゲームサーバー管理機能を MCP ベースへ移行する
- [x] 権限制御は将来拡張できる差し込みポイントを用意する
- [x] MCP 側障害時にユーザーへ返す基本的なエラー再表現を実装する

### Phase 3 完了後の改善候補

#### API 側

- MCP 利用を前提にした運用手順を runbook として別文書化する
- README に Phase 3 完了後の運用フローを追記する

#### bot 側

- 旧 REST 前提のクライアント、モック、仕様書を不要な範囲から整理する
- 実運用に応じて管理ロールなどの権限制御ポリシーを具体化する
- MCP 側障害時の再試行方針や運用アラートをさらに明文化する

## ツール分類

### 読み取り専用

- `list_servers`
- `get_server_status`
- `get_server_maintenance_notes`

### 操作系

- `start_server`
- `stop_server`

### ルール

- 読み取り専用は自動実行可
- 操作系は必ず確認を挟む
- 将来は Discord 管理ロールを条件にできるよう拡張可能にする

## Discord bot 側の確認フロー要件

最低限、次を満たすこと。

1. 操作要求を受けた時点では即実行しない
2. 対象サーバー名と実行内容を明示して確認を返す
3. ユーザーの肯定応答後にのみ MCP tool を実行する
4. タイムアウトや否定応答時は実行しない

例:

- 「`craftopia` を起動します。実行しますか？」
- 「`valheim` を停止します。実行しますか？」

## bot 側へ共有すべきインターフェース項目

別リポジトリ作業のため、少なくとも次を共有する。

- MCP transport 方式
- サーバー接続設定方法
- ツール名一覧
- 各ツールの引数と返却値
- エラー種別
- 操作系は確認必須というポリシー
- 将来ロール制御を追加する前提

## リスク

- bot 側の MCP 実装を急ぎすぎると、今度は bot 側が複雑化する
- REST と MCP の返却差分が大きいと移行が難しくなる
- 操作系の確認フローが曖昧だと事故の温床になる
- `/tell` と MCP の責務分離が崩れると二重化する

## Phase 3 の推奨順序

1. bot 側の残存する旧 REST 前提コードと文書を棚卸しする
2. `/tell` 通知を維持したまま責務分離が崩れていないかを継続確認する
3. 権限制御と障害時運用の方針を改善候補として具体化する
4. 必要に応じて API 側と bot 側の文書を更新する

## 実装完了の定義

- Discord bot 側 AI エージェントが `list_servers` と `get_server_status` を MCP 経由で利用できる
- `start_server` と `stop_server` が確認付きで実行できる
- `/tell` による通知が継続している
- 既存 REST API が移行期間中も利用可能である