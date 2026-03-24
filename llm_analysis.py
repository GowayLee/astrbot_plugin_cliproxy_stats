"""LLM analysis helpers."""

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from astrbot.api import logger
from astrbot.core.provider.provider import Provider

from constants import LLM_ANALYSIS_PROMPT


def get_llm_provider(
    context, enable_llm_analysis: bool, llm_provider_id: str
) -> Optional[Provider]:
    if not enable_llm_analysis:
        return None
    try:
        if llm_provider_id:
            provider = context.get_provider_by_id(llm_provider_id)
            if provider:
                return provider
            logger.warning(
                f"未找到指定的 Provider: {llm_provider_id}，将使用当前对话模型"
            )
        return context.get_using_provider()
    except Exception as exc:
        logger.error(f"获取 LLM Provider 失败: {exc}")
        return None


def get_available_providers(context) -> List[Dict[str, str]]:
    try:
        providers = context.get_all_providers()
        result = []
        for provider in providers:
            try:
                meta = provider.meta()
                result.append({"id": meta.id, "name": f"{meta.id} ({meta.model})"})
            except Exception:
                pass
        return result
    except Exception as exc:
        logger.error(f"获取 Provider 列表失败: {exc}")
        return []


async def generate_llm_analysis(
    context,
    enable_llm_analysis: bool,
    llm_provider_id: str,
    today_data: Dict[str, Any],
    quota_data: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    if not enable_llm_analysis:
        return None

    provider = get_llm_provider(context, enable_llm_analysis, llm_provider_id)
    if not provider:
        logger.warning("无法获取 LLM Provider，跳过智能分析")
        return None

    try:
        now = datetime.now()
        hours_elapsed = now.hour + now.minute / 60
        model_stats_text = ""
        total_requests = today_data.get("today_requests", 0)
        if today_data.get("model_stats"):
            for model in today_data["model_stats"][:15]:
                req_count = model.get("requests", 0)
                tokens = model.get("tokens", "0")
                failed = model.get("failed", 0)
                pct = (
                    round(req_count / total_requests * 100, 1)
                    if total_requests > 0
                    else 0
                )
                avg_tokens = ""
                if req_count > 0:
                    try:
                        token_str = str(tokens)
                        if "M" in token_str:
                            tok_num = float(token_str.replace("M", "")) * 1_000_000
                        elif "K" in token_str:
                            tok_num = float(token_str.replace("K", "")) * 1_000
                        else:
                            tok_num = float(tokens)
                        avg = tok_num / req_count
                        if avg >= 1000:
                            avg_tokens = f", 平均 {avg / 1000:.1f}K/次"
                        else:
                            avg_tokens = f", 平均 {int(avg)} 次"
                    except (ValueError, TypeError):
                        pass
                fail_info = f", 失败 {failed}" if failed > 0 else ""
                model_stats_text += f"- {model['name']}: {req_count} 次 ({pct}%), {tokens} tokens{avg_tokens}{fail_info}\n"
        else:
            model_stats_text = "暂无模型使用数据"

        quota_stats_text = ""
        if quota_data and quota_data.get("accounts"):
            for account in quota_data["accounts"][:8]:
                if account.get("quotas"):
                    email = account.get("email", "未知账号")
                    quota_stats_text += f"\n账号 {email}:\n"
                    for quota in account["quotas"][:8]:
                        label = quota.get("label", "")
                        percent = quota.get("percent", 0)
                        reset_time = quota.get("reset_time", "未知")
                        used = 100 - percent
                        quota_stats_text += f"  - {label}: 剩余 {percent}% (已用 {used}%), 刷新时间: {reset_time}\n"
        if not quota_stats_text:
            quota_stats_text = "暂无配额数据"

        hourly_text = ""
        if today_data.get("time_slots"):
            for slot in today_data["time_slots"]:
                hourly_text += f"- {slot['label']}: {slot['count']} 次\n"
        else:
            hourly_text = "暂无时段数据"

        prompt = LLM_ANALYSIS_PROMPT.format(
            current_time=now.strftime("%Y-%m-%d %H:%M"),
            date=today_data.get("subtitle", date.today().isoformat()),
            total_requests=today_data.get("today_requests", 0),
            total_tokens=today_data.get("today_tokens", "0"),
            success_rate=today_data.get("success_rate", 100),
            hours_elapsed=f"{hours_elapsed:.1f}",
            model_stats=model_stats_text,
            quota_stats=quota_stats_text,
            hourly_distribution=hourly_text,
        )
        response = await provider.text_chat(prompt=prompt)
        if response and response.completion_text:
            return response.completion_text
    except Exception as exc:
        logger.error(f"LLM 分析生成失败: {exc}")

    return None
