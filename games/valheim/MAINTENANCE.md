# Valheim Plugin Maintenance Notes

## 目的

Valheim の Docker ログから、Discord Bot の `/tell` に流すべき **確定イベントのみ** を抽出します。
このプラグインは、接続ノイズを通知せず、実際のプレイヤー入退場だけを Bot に伝えることを目的としています。

## 採用するイベント

通知対象は以下の2種類です。

- ログイン確定
- ログアウト確定

## イベント確定ルール

Valheim は1行だけでプレイヤー入退場を確定できないため、複数ログを相関させます。

### ログイン確定

以下の順で処理します。

1. `Got connection SteamID <steam_id>`
   - 接続候補の SteamID を保持
2. `Got character ZDOID from <character_name> : ...`
   - 保持中 SteamID とキャラクター名を対応付け
   - この時点でログイン確定とみなす

### ログアウト確定

1. `Closing socket <steam_id>`
   - SteamID から既知のキャラクター名を引く
   - 対応が取れた場合のみログアウト通知を生成

## 通知しないログ

以下は接続ノイズまたは運用ノイズとして扱い、`/tell` には流しません。

- `New connection`
- `Accepting connection k_EResultOK`
- `Connecting to Steamworks...`
- `Got status changed msg ...`
- `Connected`
- `Got handshake from client ...`
- `Server: New peer connected...`
- `RPC_Disconnect`
- `Disposing socket`
- `send queue size:0`
- `CRON[...]`
- `supervisord` の updater 系メッセージ

標準出力にはそのまま流して問題ありませんが、通知判定には使いません。

## 実ログ例と解釈

### ログイン例

```text
Got connection SteamID 76561198337666730
Got handshake from client 76561198337666730
Network version check, their:36, mine:36
Server: New peer connected,sending global keys
Got character ZDOID from Tamasan : -74706529:1
```

解釈:

- `SteamID 76561198337666730` を一時保持
- `Got character ZDOID from Tamasan` で `Tamasan` と対応付け
- ここでログイン確定

### ログアウト例

```text
RPC_Disconnect
Destroying abandoned non persistent zdo ...
Disposing socket
Closing socket 76561198337666730
```

解釈:

- `RPC_Disconnect` 単体では通知しない
- `Closing socket 76561198337666730` で SteamID 対応表を参照
- `Tamasan` が引ければログアウト確定

## tell に流す文面方針

### ログイン時

目的:

- プレイヤーの参加を自然に歓迎する
- キャラクター名を必ず発話に含める

現在の指示文面例:

```text
【システム通知】Valheimサーバー『valheim』に『Tamasan』が世界に入りました。自然で短い歓迎メッセージを作成してください。発話には必ず『Tamasan』を含めてください。
```

### ログアウト時

目的:

- 離脱したプレイヤーへ短いねぎらいを返す
- キャラクター名を必ず発話に含める

現在の指示文面例:

```text
【システム通知】Valheimサーバー『valheim』で『Tamasan』がログアウトしました。自然で短いねぎらいのメッセージを作成してください。発話には必ず『Tamasan』を含めてください。
```

## 実装上の注意

- `Got character ZDOID from ...` が来ても SteamID が未保持なら通知しない
- `Closing socket ...` が来ても SteamID 対応表に名前がなければ通知しない
- ログ行の混在を前提に、文字列完全一致ではなく必要最小限のパターンで判定する
- ログフォーマット変更時は、実ログを数十行単位で確認してから正規表現を見直す

## 改修ポイント

次のようなケースが増えた場合は、このプラグインの更新を検討します。

- 複数プレイヤー同時接続で SteamID 対応が崩れるケース
- ログローテーションや supervisor 出力形式変更
- Valheim側のアップデートによる接続ログ文言変更
- 死亡、ボス討伐、ワールドセーブ等の追加通知要望
