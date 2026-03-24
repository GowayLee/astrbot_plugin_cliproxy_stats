"""Offline preview for saved quota snapshots."""

import argparse

from _quota_debug_common import get_max_render_count, load_snapshot


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="读取 quota JSON 样本并重新渲染 `/cpa额度` 文本。"
    )
    parser.add_argument("snapshot", help="由 quota_snapshot.py 保存的 JSON 文件")
    parser.add_argument("--max-render-antigravity", type=int, default=None)
    parser.add_argument("--max-render-gemini-cli", type=int, default=None)
    parser.add_argument("--max-render-codex", type=int, default=None)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    snapshot = load_snapshot(args.snapshot)
    quota_data = snapshot.get("quota_data") or {}
    if not quota_data:
        raise SystemExit("样本中缺少 `quota_data`，无法重新渲染。")

    max_render_count = quota_data.get("max_render_count", {}).copy()
    overrides = get_max_render_count(args)
    for key, value in overrides.items():
        if value is not None:
            max_render_count[key] = value
    quota_data["max_render_count"] = max_render_count

    from text_renderer import build_text_from_data

    print(build_text_from_data(quota_data) or "❌ 数据格式化失败")


if __name__ == "__main__":
    main()
