"""Capture live quota data for later formatting tweaks."""

import argparse
from pathlib import Path

from _quota_debug_common import (
    add_common_arguments,
    ensure_credentials,
    fetch_quota_snapshot,
    run_async,
    save_snapshot,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="抓取真实 quota 数据并保存为 JSON 样本，供离线调格式使用。"
    )
    add_common_arguments(parser)
    parser.add_argument(
        "--output",
        default=str(Path("tmp") / "quota_snapshot.json"),
        help="输出 JSON 路径，默认 `tmp/quota_snapshot.json`。",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    ensure_credentials(args)
    snapshot = run_async(fetch_quota_snapshot(args))
    save_snapshot(args.output, snapshot)
    print(f"已保存 quota 样本: {args.output}")


if __name__ == "__main__":
    main()
