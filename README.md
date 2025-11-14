# 動画一括AV1変換ツール (NVIDIA NVENC 対応)

指定されたフォルダ内の MP4 動画ファイルを AV1 形式へ一括変換する Python パッケージです。
`ffmpeg` を利用し、NVIDIA NVENC (AV1) を優先して高速なハードウェアエンコードを実行します。

## ✨ 主な機能

- **AV1 への一括変換**: MP4 を AV1 コーデックに変換し、ファイルサイズ削減を図ります。
- **NVIDIA NVENC (AV1) 対応**: RTX 30 シリーズ以降など NVENC AV1 に対応した GPU 環境で高速に動作。
- **ソフトウェアフォールバック**: `--allow-software` 指定時は `libaom-av1` による CPU 変換へ自動切り替え。
- **堅牢なファイル処理**: 変換済みファイルのスキップ、ディスク空き容量チェック、重複ファイル名の自動調整を実装。
- **進捗状況の表示**: 各ファイルの変換状況、全体の進捗状況をプログレスバーで表示。
- **詳細なログ出力**: 変換結果を CSV (`convert_log.csv`) に追記し、処理サマリーを表示。

## ⚙️ 動作要件

1. **Python 3.11 以上**
2. **FFmpeg**: `ffmpeg` と `ffprobe` が `PATH` に通っていること
   - [FFmpeg 公式サイト](https://ffmpeg.org/download.html)
   - NVENC AV1 を利用する場合は対応 GPU・ドライバ・ビルドが必要
3. **NVIDIA GPU (任意)**: NVENC AV1 を使う場合は対応 GPU が必要

## 🛠️ インストール

1. [uv](https://docs.astral.sh/uv/) をインストールします。
2. このリポジトリを取得し、プロジェクトルートで以下を実行します。

   ```bash
   uv sync --all-extras
   ```

   仮想環境の作成と依存関係のインストールが完了すると、以降は `uv run <command>` でツールを利用できます。

## 🚀 使い方

### 基本コマンド

```bash
uv run python -m video_converter_av1.converter <入力フォルダ> <出力フォルダ> [オプション]
```

`video_converter_av1.converter` モジュールは `main` 関数を公開しているため、既存の Python スクリプトやワークフローから直接呼び出すこともできます。

### コマンドラインオプション

```
usage: video_converter_av1.converter [-h] [--quality QUALITY] [--no-skip-existing]
                                     [--delete-original] [--allow-software]
                                     input output

Convert MP4 files to AV1 format

positional arguments:
  input                 変換対象の動画が含まれる入力ディレクトリ
  output                変換後のファイルを格納する出力ディレクトリ

options:
  -h, --help            ヘルプを表示して終了
  --quality QUALITY     画質パラメータ (0-51、デフォルト: 28)
  --no-skip-existing    既存の出力ファイルをリネームして変換を続行
  --delete-original     変換成功後に元ファイルを削除
  --allow-software      NVENC が利用不可の場合にソフトウェアエンコードへ切り替え
```

### 📋 使用例

**1. NVENC (AV1) を利用した基本変換**

```bash
uv run python -m video_converter_av1.converter ~/Downloads ~/Converted
```

**2. 既存ファイルを上書きせず別名で保存**

```bash
uv run python -m video_converter_av1.converter ./input ./output --no-skip-existing
```

**3. ソフトウェアエンコードを許可**

```bash
uv run python -m video_converter_av1.converter ./input ./output --allow-software
```

**4. ライブラリとして利用 (Python スクリプト内から呼び出し)**

```python
from video_converter_av1.converter import main

if __name__ == "__main__":
    raise SystemExit(main(["./input", "./output", "--quality", "24"]))
```

## 📂 出力フォルダ構成とログ

- 変換結果は指定した出力ディレクトリ直下に保存され、必要に応じて重複しないファイル名へ調整されます。
- ログファイル `convert_log.csv` にはファイルごとの処理結果 (成功 / 失敗 / スキップ) が追記されます。
- サマリーには総件数・成功・失敗・スキップ件数とログファイルのパスが表示されます。

## 🧪 テスト

開発時は以下のコマンドでテストおよび静的解析を実行できます。

```bash
uv run pytest
uv run pre-commit run --all-files
```

## ©️ ライセンス

このプロジェクトは [MIT License](https://opensource.org/licenses/MIT) の下で公開されています。
