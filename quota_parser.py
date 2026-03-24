"""Quota parsing helpers."""

from datetime import datetime
from typing import Any, Dict, List, Optional


def format_reset_time(reset_time: Optional[str]) -> str:
    if not reset_time:
        return "-"
    try:
        dt = datetime.fromisoformat(reset_time.replace("Z", "+00:00"))
        return dt.astimezone().strftime("%m/%d %H:%M")
    except Exception:
        return reset_time[:16] if len(reset_time) > 16 else reset_time


def format_codex_reset_time(reset_at: Optional[int]) -> str:
    if not reset_at:
        return "-"
    try:
        return datetime.fromtimestamp(reset_at).strftime("%m/%d %H:%M")
    except Exception:
        return str(reset_at)


def parse_google_quota_dynamic(models: Dict[str, Any]) -> List[Dict[str, Any]]:
    quotas = []
    for model_id, entry in models.items():
        quota_info = entry.get("quotaInfo", entry.get("quota_info", {}))
        remaining = quota_info.get(
            "remainingFraction", quota_info.get("remaining_fraction")
        )
        reset_time = quota_info.get("resetTime", quota_info.get("reset_time"))
        if remaining is not None:
            quotas.append(
                {
                    "id": model_id,
                    "label": model_id,
                    "remaining_percent": round(remaining * 100),
                    "reset_time": reset_time,
                    "models": [model_id],
                }
            )
    quotas.sort(key=lambda item: item["remaining_percent"])
    return quotas


def parse_gemini_cli_quota_dynamic(
    buckets: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    quotas = []
    for bucket in buckets:
        model_id = bucket.get("modelId", "")
        remaining = bucket.get("remainingFraction")
        reset_time = bucket.get("resetTime")
        if model_id and remaining is not None:
            quotas.append(
                {
                    "id": model_id,
                    "label": model_id,
                    "remaining_percent": round(remaining * 100),
                    "reset_time": reset_time,
                    "models": [model_id],
                }
            )
    quotas.sort(key=lambda item: item["remaining_percent"])
    return quotas


def parse_codex_quota(
    rate_limit: Dict[str, Any], plan_type: str = "unknown"
) -> List[Dict[str, Any]]:
    quotas = []

    primary = rate_limit.get("primary_window")
    if primary:
        used_percent = primary.get("used_percent", 0)
        remaining_percent = 100 - used_percent
        reset_at = primary.get("reset_at")
        window_seconds = primary.get("limit_window_seconds", 0)
        label = "日限额" if window_seconds <= 21600 else "主限额"
        quotas.append(
            {
                "id": "codex-primary",
                "label": label,
                "remaining_percent": remaining_percent,
                "reset_time": reset_at,
                "reset_time_formatted": format_codex_reset_time(reset_at),
                "window_seconds": window_seconds,
                "models": ["codex"],
                "is_codex": True,
                "plan_type": plan_type,
            }
        )

    secondary = rate_limit.get("secondary_window")
    if secondary:
        used_percent = secondary.get("used_percent", 0)
        remaining_percent = 100 - used_percent
        reset_at = secondary.get("reset_at")
        window_seconds = secondary.get("limit_window_seconds", 0)
        label = "周限额" if window_seconds >= 604800 else "次限额"
        quotas.append(
            {
                "id": "codex-secondary",
                "label": label,
                "remaining_percent": remaining_percent,
                "reset_time": reset_at,
                "reset_time_formatted": format_codex_reset_time(reset_at),
                "window_seconds": window_seconds,
                "models": ["codex"],
                "is_codex": True,
                "plan_type": plan_type,
            }
        )

    quotas.sort(key=lambda item: item["remaining_percent"])
    return quotas
