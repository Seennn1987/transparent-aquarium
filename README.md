# 透明標本水槽 — プロトタイプ環境

このフォルダには以下がすでに用意されています（コンテナ内で動作確認済み）。

- `src/` … Three.js製の水槽シーン（プレースホルダー魚が正弦波で泳ぐ）
- `blender/generate_gerres_erythrourus.py` … Gerres erythrourusの骨格を
  数値仕様（背鰭9棘10軟条、臀鰭3棘7軟条など）から自動生成するBlenderスクリプト
- `package.json` / `vite.config.js` … `npm install && npm run build` で
  ビルドが通ることを確認済み

ここから先、あなたのPC側でのセットアップが必要です。手順を順番に記載します。

---

## 1. Node.jsのインストール（Three.js側）

まだ入っていなければ、公式サイトからLTS版を入れてください。

- https://nodejs.org/ （「LTS」と書かれた方を選択）

インストール後、ターミナルで確認:

```bash
node --version
npm --version
```

## 2. このプロジェクトを動かす

このフォルダをダウンロード後、ターミナルで:

```bash
cd transparent-aquarium
npm install
npm run dev
```

表示されるURL（例: `http://localhost:5173`）をブラウザで開くと、
発光する骨格ラインを持つプレースホルダー魚が水槽内を泳ぐのが見えるはずです。
これはBlender製アセットが完成するまでの動作確認用です。

---

## 3. Blenderのインストール

- 公式ダウンロードページ: https://www.blender.org/download/
- 推奨バージョン: **Blender 5.2 LTS**（2028年7月までサポート）
  - 4.5 LTS（2027年7月まで）でも動作しますが、5.xの方が長くサポートされます
- インストーラーの指示に従ってインストールしてください（特別な設定は不要）

## 4. uv（パッケージマネージャ）のインストール

BlenderMCPのサーバーを動かすために必要です。OSに応じたコマンドをターミナル
（Windowsは PowerShell）で実行してください。

**Mac**
```bash
brew install uv
```

**Windows (PowerShell)**
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```
実行後、以下も実行してPATHに追加してください（Claude Desktopを使う場合は再起動が必要になることがあります）。
```powershell
$localBin = "$env:USERPROFILE\.local\bin"
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
[Environment]::SetEnvironmentVariable("Path", "$userPath;$localBin", "User")
```

**Linux**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```
（`~/.local/bin` に入るので、新しいターミナルを開いてPATHが通っているか確認してください）

確認:
```bash
uv --version
```

## 5. BlenderMCPの接続設定

公式リポジトリ: https://github.com/ahujasid/blender-mcp

### 5-1. Blenderアドオンのインストール
```bash
uvx blender-mcp install-addon
```
その後、Blenderを開き、**編集 → プリファレンス → アドオン** を開いて
「Interface: Blender MCP」を検索し、チェックを入れて有効化してください。

### 5-2. MCPクライアント側の設定

**Claude Desktopを使う場合**
`Claude → 設定 → Developer → Edit Config` を開き、`claude_desktop_config.json` に
以下を追記:
```json
{
  "mcpServers": {
    "blender": {
      "command": "uvx",
      "args": ["--python", "3.11", "blender-mcp"],
      "env": { "UV_PYTHON_PREFERENCE": "only-managed" }
    }
  }
}
```
（`--python 3.11` と `UV_PYTHON_PREFERENCE=only-managed` は、Anaconda等が
入っている環境でuvが不適切なPythonを掴んで失敗するのを防ぐためのおまじないです。
Anaconda等を使っていなければ `"args": ["blender-mcp"]` だけでも動きます。）

**Claude Codeを使う場合**
```bash
claude mcp add blender uvx blender-mcp
```

### 5-3. 接続確認
1. Blenderの3Dビューポート内でNキーを押してサイドバーを開く
2. 「BlenderMCP」タブを選択
3. 「Start MCP Server」をクリック
4. Claude Desktop（またはClaude Code）を再起動し、Blenderに関する指示を出して
   反応するか確認する

**注意**: MCPサーバーは同時に1つのクライアント（Claude DesktopかCursorのどちらか）
からのみ起動してください。

---

## 6. 骨格生成スクリプトを試す

Blenderを開いた状態で、以下のどちらかの方法で
`blender/generate_gerres_erythrourus.py` を実行してください。

**方法A: Blender単体で実行（BlenderMCPなしでも可能）**
1. Blender上部タブから「Scripting」を選択
2. 「Open」から `generate_gerres_erythrourus.py` を開く
3. 「Run Script」（▷ボタン、またはAlt+P）を押す
4. 3Dビューポートに「GerresErythrourus」コレクションが現れ、
   脊柱・背鰭・臀鰭・尾鰭・外皮が生成される

**方法B: BlenderMCP経由でAIに実行させる**
接続確認ができていれば、Claude Desktop等で「このPythonスクリプトを
Blenderで実行して」と頼み、スクリプトの中身を渡すだけで同じ結果になります。
これ以降の形状調整（頭部の追加、鱗のディテール、マテリアルの微調整など）は
チャット上で指示しながら反復できます。

---

## 7. 完成したモデルをThree.js側に取り込む

Blender側で見た目を詰めたら、`ファイル → エクスポート → glTF 2.0 (.glb)`
でエクスポートし、`assets/models/gerres_erythrourus.glb` として保存してください。
その後、`src/main.js` 内の `createPlaceholderFish()` 呼び出しを
`GLTFLoader` + `AnimationMixer` に差し替える作業を、次回このチャットで一緒に行います。

---

## 困ったときは

- BlenderMCPが繋がらない: `uv cache clean blender-mcp && uvx --refresh blender-mcp` で
  キャッシュをクリアして再試行
- `npm run dev` でエラーが出る: Node.jsのバージョンが古い可能性があるため
  `node --version` が18以上か確認
