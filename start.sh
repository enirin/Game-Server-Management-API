#!/bin/bash

set -e

# スクリプトがあるディレクトリ（リポジトリのルート）に移動
cd "$(dirname "$0")"

# '.git' ディレクトリが存在するか確認し、存在する場合のみ pull する
if [ -d ".git" ]; then
    echo "🔄 リポジトリから最新のコードを取得しています..."
    git pull origin main
else
    echo "📌 Gitリポジトリとして構成されていません。最新のコード取得をスキップします。"
fi

# venv が存在しなければ作成
if [ ! -d "venv" ]; then
    echo "🐍 Python仮想環境(venv)を作成しています..."
    /usr/bin/python3 -m venv venv
fi

# 依存ライブラリをインストール
echo "📦 依存ライブラリをインストールしています..."
./venv/bin/pip install -r requirements.txt

# config.yamlが存在するかチェック
if [ ! -f "config.yaml" ]; then
    if [ -f "config.yaml.sample" ]; then
        echo "⚠️ config.yaml が存在しないため、config.yaml.sample から自動でコピーします..."
        cp config.yaml.sample config.yaml
        echo "💡 config.yaml を作成しました。"
    else
        echo "❌ config.yaml と config.yaml.sample のどちらも見つかりません。"
        exit 1
    fi
    echo "❌ 起動する前に、config.yaml を環境に合わせて編集してください。"
    exit 1
fi

echo "🚀 Botを起動しています..."
./venv/bin/python main.py
