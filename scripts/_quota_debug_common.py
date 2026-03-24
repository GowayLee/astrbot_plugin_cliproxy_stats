"""Shared helpers for local quota debugging scripts."""

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from builders import build_quota_data
from client import CPAClient
from constants import QUOTA_SUPPORTED_PROVIDERS
from text_renderer import build_text_from_data


def str_to_bool(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def add_common_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--cpa-url", default=os.getenv("CPA_URL", ""))
    parser.add_argument("--cpa-password", default=os.getenv("CPA_PASSWORD", ""))
    parser.add_argument(
        "--verify-ssl",
        action="store_true",
        default=str_to_bool(os.getenv("CPA_VERIFY_SSL", "0")),
        help="启用 SSL 校验；默认读取 CPA_VERIFY_SSL。",
    )
    parser.add_argument(
        "--max-render-antigravity",
        type=int,
        default=int(os.getenv("CPA_MAX_RENDER_ANTIGRAVITY", "10") or 10),
    )
    parser.add_argument(
        "--max-render-gemini-cli",
        type=int,
        default=int(os.getenv("CPA_MAX_RENDER_GEMINI_CLI", "10") or 10),
    )
    parser.add_argument(
        "--max-render-codex",
        type=int,
        default=int(os.getenv("CPA_MAX_RENDER_CODEX", "10") or 10),
    )


def ensure_credentials(args: argparse.Namespace) -> None:
    if args.cpa_url and args.cpa_password:
        return
    raise SystemExit(
        "缺少 CPA 连接信息，请通过参数或环境变量提供 `CPA_URL` 和 `CPA_PASSWORD`。"
    )


def get_max_render_count(args: argparse.Namespace) -> Dict[str, int]:
    return {
        "antigravity": args.max_render_antigravity,
        "gemini-cli": args.max_render_gemini_cli,
        "codex": args.max_render_codex,
    }


def normalize_cpa_url(url: str) -> str:
    value = (url or "").strip()
    if not value:
        return value
    if value.startswith(("http://", "https://")):
        return value
    return f"http://{value}"


async def render_live_quota_text(args: argparse.Namespace) -> str:
    client = CPAClient(
        normalize_cpa_url(args.cpa_url), args.cpa_password, args.verify_ssl
    )
    try:
        quota_data = await build_quota_data(client, get_max_render_count(args))
        if not quota_data:
            raise RuntimeError("获取 quota 数据失败")
        return build_text_from_data(quota_data) or "❌ 数据格式化失败"
    finally:
        await client.close()


async def fetch_quota_snapshot(args: argparse.Namespace) -> Dict[str, Any]:
    normalized_url = normalize_cpa_url(args.cpa_url)
    client = CPAClient(normalized_url, args.cpa_password, args.verify_ssl)
    try:
        max_render_count = get_max_render_count(args)
        auth_data = await client.get_auth_files()
        quota_data = await build_quota_data(client, max_render_count)
        if auth_data is None:
            raise RuntimeError("获取 auth-files 失败")

        raw_quota_results: List[Dict[str, Any]] = []
        for auth in auth_data.get("files", []):
            provider = auth.get("provider", auth.get("type", "")).lower()
            if provider not in QUOTA_SUPPORTED_PROVIDERS:
                continue

            entry = {
                "provider": provider,
                "name": auth.get("name", auth.get("id", "")),
                "email": auth.get("email", ""),
                "auth_index": auth.get("auth_index", ""),
                "disabled": auth.get("disabled", False),
                "unavailable": auth.get("unavailable", False),
            }

            if not entry["auth_index"] or entry["disabled"] or entry["unavailable"]:
                entry["quota_result"] = None
                raw_quota_results.append(entry)
                continue

            if provider == "codex":
                quota_result = await client.get_codex_quota(entry["auth_index"])
            else:
                quota_result = await client.get_google_quota(
                    entry["auth_index"], provider, entry["name"]
                )

            entry["quota_result"] = quota_result
            raw_quota_results.append(entry)

        return {
            "captured_at": datetime.now().isoformat(timespec="seconds"),
            "cpa_url": normalized_url,
            "verify_ssl": args.verify_ssl,
            "max_render_count": max_render_count,
            "auth_data": auth_data,
            "quota_data": quota_data,
            "raw_quota_results": raw_quota_results,
        }
    finally:
        await client.close()


def load_snapshot(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def save_snapshot(path: str, payload: Dict[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)
        file.write("\n")


def run_async(coro):
    return asyncio.run(coro)
