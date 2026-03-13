# Game Plugins

ゲーム固有の実装は `games/<plugin_name>/` 配下にまとめます。

基本構成:

- `plugin.py`: ゲーム固有のログ解析・通知文面・日数抽出
- `MAINTENANCE.md`: 保守者向け仕様メモ、実ログ例、通知方針
- `__init__.py`: プラグイン公開用

新しいゲームを追加すると、`games/<plugin_name>/plugin.py` は自動探索されます。
`plugin.py` 内の `ALIASES` が `servers[].game` の指定候補になります。
