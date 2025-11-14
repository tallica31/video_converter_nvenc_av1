# 単体テスト
- `tests/test_converter.py::test_run_conversion_successful_flow`
  - 正常系: NVENC が利用可能なケースで ffmpeg コマンドを実行し、ログ出力と原本削除を確認する。
- `tests/test_converter.py::test_run_conversion_error_without_software`
  - 異常系: NVENC が利用不可でソフトウェアフォールバックも禁止のケースで例外発生を確認する。

# 結合テスト
- なし

# システムテスト
- なし
