import os
import sys

# プロジェクトルートをパスに追加（games パッケージをインポート可能にするため）
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from games import create_game_plugin, get_supported_game_aliases
    print("Successfully imported games package!")
    
    aliases = get_supported_game_aliases()
    print(f"Supported games: {aliases}")
    
    valheim_plugin = create_game_plugin("valheim")
    print(f"Valheim plugin: {valheim_plugin}")
    
    print("\nImport verification: PASSED")
except Exception as e:
    print(f"Import verification: FAILED")
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
