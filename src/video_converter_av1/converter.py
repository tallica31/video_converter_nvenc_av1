from __future__ import annotations

import argparse
import csv
import os
import shutil
import subprocess
import sys
from enum import Enum
from pathlib import Path
from typing import Sequence

from pydantic import BaseModel, ConfigDict, Field, field_validator
from tqdm import tqdm


class ConversionStatus(str, Enum):
    """ログファイルに記録する変換ステータス。"""

    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class ConverterSettings(BaseModel):
    """変換処理で使用する設定値。"""

    input_dir: Path = Field(alias="input")
    output_dir: Path = Field(alias="output")
    quality: int = 28
    skip_existing: bool = True
    delete_original: bool = False
    allow_software: bool = False

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("quality")
    @classmethod
    def validate_quality(cls, value: int) -> int:
        """画質パラメータの許容範囲を検証する。"""

        if not 0 <= value <= 51:
            raise ValueError("quality は 0-51 の範囲で指定してください")
        return value


class ConversionSummary(BaseModel):
    """最終サマリー表示用の統計情報。"""

    total: int = 0
    success: int = 0
    failed: int = 0
    skipped: int = 0

    model_config = ConfigDict(validate_assignment=True)

    def register(self, status: ConversionStatus) -> None:
        """ファイル単位の結果をサマリーへ反映する。"""

        self.total += 1
        if status is ConversionStatus.SUCCESS:
            self.success += 1
        elif status is ConversionStatus.FAILED:
            self.failed += 1
        else:
            self.skipped += 1


class ConversionLogEntry(BaseModel):
    """CSV に書き出す単一ファイルの処理結果。"""

    input_path: Path
    output_path: Path | None
    status: ConversionStatus
    message: str | None = None


class ConversionSkip(RuntimeError):
    """ユーザー設定により処理をスキップする際に発生させる例外。"""


def parse_arguments(args: Sequence[str] | None = None) -> ConverterSettings:
    """コマンドライン引数を解析して設定モデルへ変換する。"""

    parser = argparse.ArgumentParser(description="Convert MP4 files to AV1 format")
    parser.add_argument("input", help="変換対象の動画が含まれる入力ディレクトリ")
    parser.add_argument("output", help="変換後のファイルを格納する出力ディレクトリ")
    parser.add_argument(
        "--quality",
        type=int,
        default=28,
        help="画質パラメータ (0-51、デフォルト: 28)",
    )
    parser.add_argument(
        "--no-skip-existing",
        action="store_true",
        help="既存の出力ファイルをリネームして変換を続行",
    )
    parser.add_argument(
        "--delete-original",
        action="store_true",
        help="変換成功後に元ファイルを削除",
    )
    parser.add_argument(
        "--allow-software",
        action="store_true",
        help="NVENC が利用不可の場合にソフトウェアエンコードへ切り替え",
    )
    namespace = parser.parse_args(args)
    return ConverterSettings(
        input=Path(namespace.input).expanduser().resolve(),
        output=Path(namespace.output).expanduser().resolve(),
        quality=namespace.quality,
        skip_existing=not namespace.no_skip_existing,
        delete_original=namespace.delete_original,
        allow_software=namespace.allow_software,
    )


def collect_target_files(input_dir: Path) -> list[Path]:
    """入力ディレクトリ配下の MP4 ファイル一覧を取得する。"""

    if not input_dir.exists():
        raise FileNotFoundError(f"入力ディレクトリが存在しません: {input_dir}")
    files = [path for path in input_dir.rglob("*.mp4") if path.is_file()]
    files.sort()
    return files


def ensure_output_directory(output_dir: Path) -> None:
    """出力ディレクトリを作成し、書き込み可能か確認する。"""

    output_dir.mkdir(parents=True, exist_ok=True)
    if not os_access_writable(output_dir):
        raise PermissionError(f"出力ディレクトリへ書き込みできません: {output_dir}")


def os_access_writable(path: Path) -> bool:
    """指定パスが書き込み可能かを判定する。"""

    return os.access(path, os.W_OK)


def select_encoder(allow_software: bool) -> str:
    """利用可能なエンコーダーを判定し、コーデック名を返す。"""

    if is_nvenc_available():
        return "av1_nvenc"
    if allow_software:
        return "libaom-av1"
    msg = "NVENC (AV1) が利用できず、ソフトウェアフォールバックも許可されていません"
    raise RuntimeError(msg)


def is_nvenc_available() -> bool:
    """ffmpeg のエンコーダー一覧を参照し NVENC の利用可否を判定する。"""

    try:
        result = subprocess.run(
            ["ffmpeg", "-hide_banner", "-encoders"],
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:  # pragma: no cover - 実行環境依存
        raise FileNotFoundError("ffmpeg コマンドが見つかりません") from exc
    return "av1_nvenc" in result.stdout


def ensure_disk_capacity(target_dir: Path, required_bytes: int) -> None:
    """出力先ドライブの空き容量が十分かどうかを検証する。"""

    usage = shutil.disk_usage(target_dir)
    if usage.free < required_bytes:
        raise RuntimeError("ディスクの空き容量が不足しています")


def build_output_path(file_path: Path, settings: ConverterSettings) -> Path:
    """入力ファイルに対応する出力ファイルのパスを生成する。"""

    relative = file_path.relative_to(settings.input_dir)
    candidate = (settings.output_dir / relative).with_suffix(".mkv")
    candidate.parent.mkdir(parents=True, exist_ok=True)
    if candidate.exists():
        if settings.skip_existing:
            raise ConversionSkip("既存の出力をスキップしました")
        return generate_unique_path(candidate)
    return candidate


def generate_unique_path(base_path: Path) -> Path:
    """重複ファイル名を避けるためのパスを生成する。"""

    stem = base_path.stem
    suffix = base_path.suffix
    parent = base_path.parent
    counter = 1
    new_path = base_path
    while new_path.exists():
        new_path = parent / f"{stem}_{counter}{suffix}"
        counter += 1
    return new_path


def build_ffmpeg_command(
    input_path: Path, output_path: Path, encoder: str, quality: int
) -> list[str]:
    """ffmpeg 実行コマンドを組み立てる。"""

    command = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-stats",
        "-i",
        str(input_path),
        "-c:v",
        encoder,
    ]
    if encoder == "av1_nvenc":
        command += ["-cq", str(quality), "-b:v", "0", "-preset", "p5"]
    else:
        command += ["-crf", str(quality), "-b:v", "0", "-cpu-used", "4"]
    command += ["-c:a", "copy", str(output_path)]
    return command


def append_log_entry(log_path: Path, entry: ConversionLogEntry) -> None:
    """CSV ログファイルへエントリを追記する。"""

    log_path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not log_path.exists()
    with log_path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        if write_header:
            writer.writerow(["input", "output", "status", "message"])
        writer.writerow(
            [
                str(entry.input_path),
                str(entry.output_path) if entry.output_path else "",
                entry.status.value,
                entry.message or "",
            ]
        )


def convert_single_file(
    file_path: Path,
    settings: ConverterSettings,
    encoder: str,
) -> ConversionLogEntry:
    """単一ファイルの変換処理を実行する。"""

    output_path = build_output_path(file_path, settings)
    ensure_disk_capacity(output_path.parent, file_path.stat().st_size)
    command = build_ffmpeg_command(file_path, output_path, encoder, settings.quality)
    subprocess.run(command, check=True)
    if settings.delete_original:
        file_path.unlink(missing_ok=True)
    return ConversionLogEntry(
        input_path=file_path,
        output_path=output_path,
        status=ConversionStatus.SUCCESS,
        message=None,
    )


def run_conversion(settings: ConverterSettings) -> int:
    """設定値に基づき一連の変換処理を実行する。"""

    files = collect_target_files(settings.input_dir)
    ensure_output_directory(settings.output_dir)
    encoder = select_encoder(settings.allow_software)
    log_path = settings.output_dir / "convert_log.csv"
    summary = ConversionSummary()
    progress_bar = tqdm(files, unit="file", disable=not sys.stdout.isatty())
    for file_path in progress_bar:
        progress_bar.set_description(file_path.name)
        try:
            entry = convert_single_file(file_path, settings, encoder)
        except ConversionSkip as skip_error:
            entry = ConversionLogEntry(
                input_path=file_path,
                output_path=None,
                status=ConversionStatus.SKIPPED,
                message=str(skip_error),
            )
        except Exception as error:  # pragma: no cover - 想定外エラー
            entry = ConversionLogEntry(
                input_path=file_path,
                output_path=None,
                status=ConversionStatus.FAILED,
                message=str(error),
            )
        append_log_entry(log_path, entry)
        summary.register(entry.status)
    progress_bar.close()
    print_summary(summary, log_path)
    return 0 if summary.failed == 0 else 1


def print_summary(summary: ConversionSummary, log_path: Path) -> None:
    """処理結果のサマリーを標準出力へ表示する。"""

    print("=== Conversion Summary ===")
    print(f"Total   : {summary.total}")
    print(f"Success : {summary.success}")
    print(f"Failed  : {summary.failed}")
    print(f"Skipped : {summary.skipped}")
    print(f"Log file: {log_path}")


def main(argv: Sequence[str] | None = None) -> int:
    """エントリーポイント。引数を解析し変換処理を実行する。"""

    settings = parse_arguments(argv)
    return run_conversion(settings)


__all__ = [
    "ConversionStatus",
    "ConverterSettings",
    "ConversionSummary",
    "main",
    "run_conversion",
]
