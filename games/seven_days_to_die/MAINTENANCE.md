# 7 Days to Die Plugin Maintenance Notes

## 目的

7 Days to Die のログから、プレイヤーの参加/退出を検知して Discord Bot の `/tell` に渡します。

## 現在の検知対象

### ログイン候補

- `Player connected ... name=<player_name>`
- `Player '<player_name>' joined the game`

### ログアウト候補

- `Player disconnected: <player_name>`
- `Player '<player_name>' left the game`

## tell に流す文面方針

### ログイン時

```text
【システム通知】7 Days to Dieサーバー『7d2d』に『Alice』が参加しました。自然で短い歓迎メッセージを作成してください。発話には必ず『Alice』を含めてください。
```

### ログアウト時

```text
【システム通知】7 Days to Dieサーバー『7d2d』で『Alice』が退出しました。自然で短いねぎらいメッセージを作成してください。発話には必ず『Alice』を含めてください。
```

## 改修時の注意

- 7 Days to Die は導入方法やMOD構成でログ形式差分が出やすいです
- 実ログをもとに正規表現を追加する場合は、既存パターンを壊さないように追加ベースで対応してください
- ログイン/ログアウト以外のイベントを追加したい場合は、`PresenceEvent` 以外のイベント型追加も検討してください
