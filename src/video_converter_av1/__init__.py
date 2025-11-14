"""動画変換パッケージ。"""

from __future__ import annotations

from typing import TYPE_CHECKING, Sequence

if TYPE_CHECKING:
    from .converter import ConverterSettings

__all__ = ["main", "run_conversion"]


def main(argv: Sequence[str] | None = None) -> int:
    """エントリーポイントの遅延ロードラッパー。"""

    from .converter import main as converter_main

    return converter_main(argv)


def run_conversion(settings: "ConverterSettings") -> int:
    """変換処理関数の遅延ロードラッパー。"""

    from .converter import run_conversion as converter_run

    return converter_run(settings)
