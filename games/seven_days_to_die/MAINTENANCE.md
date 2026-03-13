# 7 Days to Die Plugin Maintenance Notes

## 目的

7 Days to Die のログから、プレイヤーの参加/退出/死亡を検知して Discord Bot の `/tell` に渡します。

## 現在の検知対象

### ログイン候補

- `Player '<player_name>' joined the game`

### ログアウト候補

- `Player '<player_name>' left the game`

### 死亡候補

- `Player '<player_name>' died`

## tell に流す文面方針

### ログイン時

```text
【システム通知】7 Days to Dieサーバー『7d2d』に『Alice』が参加しました。自然で短い歓迎メッセージを作成してください。発話には必ず『Alice』を含めてください。
```

### ログアウト時

```text
【システム通知】7 Days to Dieサーバー『7d2d』で『Alice』が退出しました。自然で短いねぎらいメッセージを作成してください。発話には必ず『Alice』を含めてください。
```

### 死亡時

```text
【システム通知】7 Days to Dieサーバー『7d2d』で『Alice』が死亡しました。ゾンビに倒されたことを揶揄するような、短くウィットに富んだ煽り気味のメッセージを作成してください。発話には必ず『Alice』を含めてください。
```

## 改修時の注意

- 7 Days to Die は導入方法やMOD構成でログ形式差分が出やすいです
- ゲーム内チャットへ送った文章がログに書かれる環境では、広い接続ログを拾うと tell の自己反映で重複通知になりやすいため、まずは `joined the game` / `left the game` の確定ログを優先してください
- 実ログをもとに正規表現を追加する場合は、誤検知と重複通知を避けられるかを先に確認してください
- ログイン/ログアウト以外のイベントを追加したい場合は、`PresenceEvent` 以外のイベント型追加も検討してください
