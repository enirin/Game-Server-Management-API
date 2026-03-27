# MCP 移行計画

## 目的

`Game-Server-Management-API` が提供するゲームサーバー管理機能を MCP サーバーとして公開し、Discord bot 側の AI エージェント機能を、より保守しやすい責務分離で再構成する。

本計画は、別リポジトリで作業する Discord bot 側との連携前提で、作業順序、受け渡し事項、確認ポイントを整理するためのものです。

## 前提となる決定事項

詳細は [ADR 0001](./adr/0001-mcp-based-game-server-management.md) を参照。

Phase 1 の詳細設計は [MCP Phase 1 詳細設計](./mcp-phase1-detailed-design.md) を参照。

Discord bot 実装担当者向けの接続契約は [Discord Bot 向け MCP 接続契約](./mcp-bot-connection-contract.md) を参照。

- 管理サービス側は Flask API と MCP サーバーを併存させる
- Discord bot 側は MCP ホストとして実装する
- `/tell` 通知は初期段階では維持する
- 読み取り専用ツールと操作ツールを分離する
- `start_server` / `stop_server` は確認必須
- 初期段階では誰でも操作要求できる前提でよい
- 将来的に Discord の管理ロール条件を追加できるようにする

## フェーズ構成

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

## Phase 2: Discord bot 側に MCP ホストを追加

### bot 側で必要な検討

- MCP サーバー接続方式
  - ローカル同居なら `stdio`
  - 別プロセス / 別ホストなら `streamable HTTP` を優先
- AI エージェントにどのツールを見せるか
- 操作前確認をどう実装するか
- 実行者情報をどこまでツール呼び出しへ渡すか

### bot 側で必要な改修

- MCP ホスト実装の追加
- サーバー管理 MCP の登録
- 読み取り系と操作系で異なる実行ポリシーの実装
- `start_server` / `stop_server` の確認フロー実装
- 将来のロール制御に備えた権限判定ポイントの追加

### このリポジトリから bot 側へ渡すべき情報

- MCP ツール一覧
- 引数仕様
- 返却スキーマ
- エラー分類
- 推奨確認文面のたたき台
- 接続 URL と transport の既定値

### 完了条件

- bot 側 AI エージェントが MCP で状態照会できる
- bot 側から確認付きで起動停止できる

## Phase 3: 移行と運用安定化

### このリポジトリで行うこと

- 保守情報を MCP resource として参照可能にする
- 必要なら説明用 prompt / helper を追加する
- ドキュメント更新

### Discord bot 側で行うこと

- 既存 REST 呼び出しのうち読み取り系を MCP へ置換
- 問題なければ操作系も MCP へ移行
- `/tell` はそのまま維持

### 完了条件

- bot 側の主要なサーバー管理機能が MCP ベースへ移行済み
- 既存通知フローは維持されている

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

## 当面の推奨順序

1. このリポジトリで MCP サーバー骨格と共通サービス層を作る
2. 最小ツールセットを公開する
3. bot 側に MCP ホストを実装する
4. 読み取り系から移行する
5. 操作系を確認付きで移行する

## 実装完了の定義

- Discord bot 側 AI エージェントが `list_servers` と `get_server_status` を MCP 経由で利用できる
- `start_server` と `stop_server` が確認付きで実行できる
- `/tell` による通知が継続している
- 既存 REST API が移行期間中も利用可能である