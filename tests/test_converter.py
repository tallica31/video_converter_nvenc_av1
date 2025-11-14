from __future__ import annotations

import csv
from pathlib import Path
from types import SimpleNamespace

import pytest

from video_converter_av1.converter import ConverterSettings, run_conversion


@pytest.fixture()
def fake_ffmpeg(monkeypatch):
    """ffmpeg 呼び出しを記録し、外部プロセスを起動しないスタブ。"""

    calls: list[list[str]] = []

    def stub(command: list[str], check: bool) -> SimpleNamespace:
        calls.append(command)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr("video_converter_av1.converter.subprocess.run", stub)
    return calls


def create_sample_file(path: Path) -> None:
    """空の MP4 ファイルを生成する。"""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"0" * 1024)


def test_run_conversion_successful_flow(tmp_path, monkeypatch, fake_ffmpeg):
    """NVENC 利用時に正常終了し、ログが残ることを検証する。"""

    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    create_sample_file(input_dir / "sample.mp4")
    monkeypatch.setattr("video_converter_av1.converter.is_nvenc_available", lambda: True)

    settings = ConverterSettings(
        input_dir=input_dir,
        output_dir=output_dir,
        delete_original=True,
    )
    exit_code = run_conversion(settings)

    assert exit_code == 0
    assert not (input_dir / "sample.mp4").exists()
    assert fake_ffmpeg, "ffmpeg コマンドが呼び出されていません"

    log_path = output_dir / "convert_log.csv"
    with log_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["status"] == "success"
    assert rows[0]["output"].endswith(".mkv")


def test_run_conversion_error_without_software(monkeypatch, tmp_path):
    """NVENC もソフトウェアも利用できない場合は例外が発生する。"""

    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    create_sample_file(input_dir / "sample.mp4")
    monkeypatch.setattr("video_converter_av1.converter.is_nvenc_available", lambda: False)

    settings = ConverterSettings(input_dir=input_dir, output_dir=output_dir)

    with pytest.raises(RuntimeError):
        run_conversion(settings)
