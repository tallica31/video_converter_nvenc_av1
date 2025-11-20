"""開発環境で src 配下のパッケージを直接読み込むためのラッパー。"""

from __future__ import annotations

import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

SRC_PACKAGE = Path(__file__).resolve().parent.parent / "src" / "video_converter_av1"
PACKAGE_INIT = SRC_PACKAGE / "__init__.py"
SPEC = spec_from_file_location(
    "video_converter_av1",
    PACKAGE_INIT,
    submodule_search_locations=[str(SRC_PACKAGE)],
)
if SPEC is None or SPEC.loader is None:  # pragma: no cover - 異常系
    raise ImportError("動画変換モジュールを読み込めませんでした")
MODULE = module_from_spec(SPEC)
sys.modules[__name__] = MODULE
SPEC.loader.exec_module(MODULE)
