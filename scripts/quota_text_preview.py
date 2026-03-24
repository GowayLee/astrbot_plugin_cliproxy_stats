"""Live preview for the final `/cpa额度` text output."""

import argparse

from _quota_debug_common import (
    add_common_arguments,
    ensure_credentials,
    render_live_quota_text,
    run_async,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="从真实 CPA 环境拉取数据，直接打印 `/cpa额度` 最终文本。"
    )
    add_common_arguments(parser)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    ensure_credentials(args)
    print(run_async(render_live_quota_text(args)))


if __name__ == "__main__":
    main()
