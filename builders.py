"""Structured data builders for plugin commands."""

from datetime import date, datetime
from typing import Any, Callable, Dict, Optional

from constants import PROVIDER_INFO, QUOTA_SUPPORTED_PROVIDERS
from quota_parser import (
    format_reset_time,
    parse_codex_quota,
    parse_gemini_cli_quota_dynamic,
    parse_google_quota_dynamic,
)


def format_tokens(tokens: int) -> str:
    if tokens >= 1_000_000:
        return f"{tokens / 1_000_000:.2f}M"
    if tokens >= 1_000:
        return f"{tokens / 1_000:.2f}K"
    return str(tokens)


def get_provider_display(provider: str) -> str:
    mapping = {
        "gemini": "Gemini",
        "claude": "Claude",
        "codex": "OpenAI/Codex",
        "antigravity": "Antigravity",
        "iflow": "iFlow",
        "qwen": "Qwen",
    }
    return mapping.get(provider.lower(), provider)


async def build_overview_data(client) -> Optional[Dict[str, Any]]:
    usage_data = await client.get_usage()
    auth_data = await client.get_auth_files()
    if not usage_data:
        return None

    usage = usage_data.get("usage", {})
    total_requests = usage.get("total_requests", 0)
    success_count = usage.get("success_count", 0)
    failure_count = usage.get("failure_count", 0)
    total_tokens = usage.get("total_tokens", 0)
    success_rate = (
        round((success_count / total_requests * 100), 1) if total_requests > 0 else 0
    )

    api_list = []
    apis = usage.get("apis", {})
    if apis:
        sorted_apis = sorted(
            apis.items(),
            key=lambda item: item[1].get("total_requests", 0),
            reverse=True,
        )
        for api_name, api_data in sorted_apis[:8]:
            api_list.append(
                {
                    "name": api_name,
                    "requests": api_data.get("total_requests", 0),
                    "tokens": format_tokens(api_data.get("total_tokens", 0)),
                }
            )

    auth_info = None
    if auth_data and auth_data.get("files"):
        auth_files = auth_data.get("files", [])
        active_count = sum(
            1
            for item in auth_files
            if not item.get("disabled", False) and not item.get("unavailable", False)
        )
        type_counts: Dict[str, Dict[str, int]] = {}
        for auth in auth_files:
            provider = auth.get("provider", auth.get("type", "unknown"))
            type_counts.setdefault(provider, {"total": 0, "active": 0})
            type_counts[provider]["total"] += 1
            if not auth.get("disabled", False) and not auth.get("unavailable", False):
                type_counts[provider]["active"] += 1

        providers = [
            {
                "name": get_provider_display(provider),
                "active": counts["active"],
                "total": counts["total"],
            }
            for provider, counts in type_counts.items()
        ]
        auth_info = {
            "active": active_count,
            "total": len(auth_files),
            "providers": providers,
        }

    return {
        "stats_type": "overview",
        "title": "📊 CLIProxyAPI 统计",
        "subtitle": "总览",
        "total_requests": total_requests,
        "success_count": success_count,
        "failure_count": failure_count,
        "success_rate": success_rate,
        "total_tokens": format_tokens(total_tokens),
        "apis": api_list,
        "auth_info": auth_info,
        "query_time": datetime.now().strftime("%H:%M:%S"),
    }


async def build_today_data(client) -> Optional[Dict[str, Any]]:
    usage_data = await client.get_usage()
    if not usage_data:
        return None

    usage = usage_data.get("usage", {})
    today = date.today().isoformat()
    requests_by_day = usage.get("requests_by_day", {})
    tokens_by_day = usage.get("tokens_by_day", {})
    today_requests = requests_by_day.get(today, 0)
    today_tokens = tokens_by_day.get(today, 0)

    apis = usage.get("apis", {})
    model_stats = []
    today_by_hour: Dict[int, int] = {hour: 0 for hour in range(24)}
    auth_usage: Dict[str, Dict[str, Any]] = {}
    total_input_tokens = 0
    total_output_tokens = 0
    total_reasoning_tokens = 0
    total_cached_tokens = 0

    if apis:
        model_aggregated: Dict[str, Dict[str, Any]] = {}
        for _, api_data in apis.items():
            models = api_data.get("models", {})
            for model_name, model_data in models.items():
                details = model_data.get("details", [])
                today_details = [
                    detail
                    for detail in details
                    if str(detail.get("timestamp", "")).startswith(today)
                ]
                if not today_details:
                    continue

                model_aggregated.setdefault(
                    model_name,
                    {
                        "requests": 0,
                        "tokens": 0,
                        "failed": 0,
                        "input_tokens": 0,
                        "output_tokens": 0,
                        "reasoning_tokens": 0,
                        "cached_tokens": 0,
                    },
                )

                for detail in today_details:
                    model_aggregated[model_name]["requests"] += 1
                    tokens_info = detail.get("tokens", {})
                    input_tok = tokens_info.get("input_tokens", 0)
                    output_tok = tokens_info.get("output_tokens", 0)
                    reasoning_tok = tokens_info.get("reasoning_tokens", 0)
                    cached_tok = tokens_info.get("cached_tokens", 0)
                    total_tok = tokens_info.get("total_tokens", 0)

                    model_aggregated[model_name]["tokens"] += total_tok
                    model_aggregated[model_name]["input_tokens"] += input_tok
                    model_aggregated[model_name]["output_tokens"] += output_tok
                    model_aggregated[model_name]["reasoning_tokens"] += reasoning_tok
                    model_aggregated[model_name]["cached_tokens"] += cached_tok

                    total_input_tokens += input_tok
                    total_output_tokens += output_tok
                    total_reasoning_tokens += reasoning_tok
                    total_cached_tokens += cached_tok

                    if detail.get("failed", False):
                        model_aggregated[model_name]["failed"] += 1

                    auth_index = detail.get("auth_index", "unknown")
                    auth_usage.setdefault(
                        auth_index, {"requests": 0, "tokens": 0, "failed": 0}
                    )
                    auth_usage[auth_index]["requests"] += 1
                    auth_usage[auth_index]["tokens"] += total_tok
                    if detail.get("failed", False):
                        auth_usage[auth_index]["failed"] += 1

                    timestamp = str(detail.get("timestamp", ""))
                    try:
                        today_by_hour[int(timestamp[11:13])] += 1
                    except (ValueError, IndexError):
                        pass

        model_list = [
            (
                name,
                data["requests"],
                data["tokens"],
                data["failed"],
                data["input_tokens"],
                data["output_tokens"],
                data["reasoning_tokens"],
                data["cached_tokens"],
            )
            for name, data in model_aggregated.items()
        ]
        model_list.sort(key=lambda item: item[1], reverse=True)
        for item in model_list[:15]:
            (
                model_name,
                req_count,
                tok_count,
                fail_count,
                in_tok,
                out_tok,
                reason_tok,
                cache_tok,
            ) = item
            model_stats.append(
                {
                    "name": model_name,
                    "requests": req_count,
                    "tokens": format_tokens(tok_count),
                    "failed": fail_count,
                    "input_tokens": in_tok,
                    "output_tokens": out_tok,
                    "reasoning_tokens": reason_tok,
                    "cached_tokens": cache_tok,
                }
            )

    time_slots = [
        {
            "label": "凌晨 0-6",
            "count": sum(today_by_hour[hour] for hour in range(0, 6)),
        },
        {
            "label": "上午 6-12",
            "count": sum(today_by_hour[hour] for hour in range(6, 12)),
        },
        {
            "label": "下午 12-18",
            "count": sum(today_by_hour[hour] for hour in range(12, 18)),
        },
        {
            "label": "晚间 18-24",
            "count": sum(today_by_hour[hour] for hour in range(18, 24)),
        },
    ]

    auth_stats = [
        {
            "auth_index": auth_id,
            "requests": stats["requests"],
            "tokens": format_tokens(stats["tokens"]),
            "failed": stats["failed"],
        }
        for auth_id, stats in sorted(
            auth_usage.items(), key=lambda item: item[1]["requests"], reverse=True
        )[:10]
    ]

    total_failed = sum(item.get("failed", 0) for item in model_stats)
    success_rate = (
        round((today_requests - total_failed) / today_requests * 100, 1)
        if today_requests > 0
        else 100
    )

    return {
        "stats_type": "today",
        "title": "📅 今日使用统计",
        "subtitle": today,
        "today_requests": today_requests,
        "today_tokens": format_tokens(today_tokens),
        "success_rate": success_rate,
        "model_stats": model_stats if model_stats else None,
        "time_slots": time_slots
        if sum(item["count"] for item in time_slots) > 0
        else None,
        "auth_stats": auth_stats if auth_stats else None,
        "token_breakdown": {
            "input": format_tokens(total_input_tokens),
            "output": format_tokens(total_output_tokens),
            "reasoning": format_tokens(total_reasoning_tokens),
            "cached": format_tokens(total_cached_tokens),
        },
        "query_time": datetime.now().strftime("%H:%M:%S"),
    }


async def build_quota_data(
    client,
    max_render_count: Dict[str, int],
    log_debug: Optional[Callable[[str], None]] = None,
) -> Optional[Dict[str, Any]]:
    auth_data = await client.get_auth_files()
    if not auth_data:
        return None

    auth_files = auth_data.get("files", [])
    if not auth_files:
        return {
            "stats_type": "quota",
            "title": "📊 OAuth 配额状态",
            "subtitle": "无账号",
            "accounts": [],
            "provider_groups": [],
            "empty_state": "no_accounts",
            "query_time": datetime.now().strftime("%H:%M:%S"),
            "max_render_count": max_render_count,
        }

    quota_auths = [
        auth
        for auth in auth_files
        if auth.get("provider", auth.get("type", "")).lower()
        in QUOTA_SUPPORTED_PROVIDERS
    ]
    if not quota_auths:
        supported_names = [
            PROVIDER_INFO.get(name, {}).get("name", name)
            for name in QUOTA_SUPPORTED_PROVIDERS
        ]
        return {
            "stats_type": "quota",
            "title": "📊 OAuth 配额状态",
            "subtitle": "无支持账号",
            "accounts": [],
            "provider_groups": [],
            "empty_state": "no_supported_accounts",
            "supported_provider_names": supported_names,
            "query_time": datetime.now().strftime("%H:%M:%S"),
            "max_render_count": max_render_count,
        }

    provider_groups: Dict[str, Any] = {}
    for auth in quota_auths:
        provider = auth.get("provider", auth.get("type", "unknown")).lower()
        display_provider = "gemini" if provider == "gemini-cli" else provider
        provider_groups.setdefault(display_provider, []).append(auth)

    accounts = []
    for provider, auths in provider_groups.items():
        provider_info = PROVIDER_INFO.get(
            provider, {"name": provider.title(), "icon": "📦", "color": "#999999"}
        )
        for auth in auths:
            auth_index = auth.get("auth_index", "")
            email = auth.get("email", "")
            name = auth.get("name", auth.get("id", "未知"))
            disabled = auth.get("disabled", False)
            unavailable = auth.get("unavailable", False)
            original_provider = auth.get(
                "provider", auth.get("type", "unknown")
            ).lower()

            icon = "❌" if (disabled or unavailable) else "✅"
            display = email if email else name
            if len(display) > 30:
                display = display[:27] + "..."

            account_data = {
                "icon": icon,
                "email": display,
                "provider": provider,
                "provider_name": provider_info["name"],
                "provider_icon": provider_info["icon"],
                "provider_color": provider_info["color"],
                "error": None,
                "quotas": [],
            }

            if not auth_index:
                account_data["error"] = "无法获取配额（缺少 auth_index）"
                accounts.append(account_data)
                continue

            if disabled or unavailable:
                account_data["error"] = "账号已禁用或不可用"
                accounts.append(account_data)
                continue

            if log_debug:
                log_debug(
                    f"正在获取配额: provider={original_provider}, name={name}, auth_index={auth_index}"
                )

            if original_provider == "codex":
                quota_result = await client.get_codex_quota(auth_index)
            else:
                quota_result = await client.get_google_quota(
                    auth_index, original_provider, name
                )

            if not quota_result.get("success"):
                error_code = quota_result.get("error_code", 0)
                if error_code == 403:
                    account_data["error"] = "不支持配额查询"
                    account_data["error_detail"] = "此凭证类型暂不支持配额查询"
                else:
                    account_data["error"] = quota_result.get("error", "获取配额失败")
                accounts.append(account_data)
                continue

            if original_provider == "codex":
                rate_limit = quota_result.get("rate_limit", {})
                if not rate_limit:
                    account_data["error"] = "无配额信息"
                    accounts.append(account_data)
                    continue
                quota_groups = parse_codex_quota(
                    rate_limit, quota_result.get("plan_type", "unknown")
                )
            elif original_provider in ("gemini", "gemini-cli"):
                buckets = quota_result.get("buckets", [])
                if not buckets:
                    account_data["error"] = "无配额信息"
                    accounts.append(account_data)
                    continue
                quota_groups = parse_gemini_cli_quota_dynamic(buckets)
            else:
                models = quota_result.get("models", {})
                if not models:
                    account_data["error"] = "无可用模型"
                    accounts.append(account_data)
                    continue
                quota_groups = parse_google_quota_dynamic(models)

            if not quota_groups:
                account_data["error"] = "无配额信息"
                accounts.append(account_data)
                continue

            for group in quota_groups:
                percent = group["remaining_percent"]
                if group.get("is_codex"):
                    reset_time = group.get("reset_time_formatted", "-")
                else:
                    reset_time = format_reset_time(group.get("reset_time"))

                if percent >= 80:
                    status_icon = "🟢"
                    color = "#10b981"
                    level = "high"
                elif percent >= 50:
                    status_icon = "🟡"
                    color = "#f59e0b"
                    level = "medium"
                elif percent >= 20:
                    status_icon = "🟠"
                    color = "#f97316"
                    level = "medium"
                else:
                    status_icon = "🔴"
                    color = "#ef4444"
                    level = "low"

                account_data["quotas"].append(
                    {
                        "label": group["label"],
                        "icon": status_icon,
                        "percent": percent,
                        "color": color,
                        "level": level,
                        "reset_time": reset_time,
                    }
                )

            accounts.append(account_data)

    provider_summary = []
    for provider in provider_groups.keys():
        info = PROVIDER_INFO.get(provider, {"name": provider.title(), "icon": "📦"})
        count = len(
            [account for account in accounts if account.get("provider") == provider]
        )
        provider_summary.append(f"{info['icon']} {info['name']} ({count})")

    return {
        "stats_type": "quota",
        "title": "📊 OAuth 配额状态",
        "subtitle": " | ".join(provider_summary) if provider_summary else "无账号",
        "accounts": accounts,
        "provider_groups": list(provider_groups.keys()),
        "query_time": datetime.now().strftime("%H:%M:%S"),
        "max_render_count": max_render_count,
    }
