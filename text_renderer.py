"""Text rendering helpers for command output."""

from typing import Any, Dict, List, Optional


def _build_quota_account_title(
    account: Dict[str, Any], display_counts: Dict[str, int]
) -> str:
    display = account.get("email", "未知账号")
    auth_index = account.get("auth_index", "")
    if auth_index and display_counts.get(display, 0) > 1:
        return f"{account.get('icon', '•')} {display} [{auth_index}]"
    return f"{account.get('icon', '•')} {display}"


def build_text_from_data(data: Dict[str, Any]) -> Optional[str]:
    stats_type = data.get("stats_type", "")
    lines: List[str] = []

    if stats_type == "overview":
        lines.append(data.get("title", "📊 CLIProxyAPI 统计"))
        lines.append("")
        lines.append("总体统计")
        lines.append(f"- 总请求数: {data.get('total_requests', 0)}")
        lines.append(f"- 成功率: {data.get('success_rate', 0)}%")
        lines.append(
            f"- 成功/失败: {data.get('success_count', 0)} / {data.get('failure_count', 0)}"
        )
        lines.append(f"- 总 Token: {data.get('total_tokens', '0')}")
        apis = data.get("apis", [])
        if apis:
            lines.append("")
            lines.append("各接口统计")
            for api in apis[:8]:
                lines.append(f"- {api['name']}: {api['requests']} 次 / {api['tokens']}")
        auth_info = data.get("auth_info")
        if auth_info:
            lines.append("")
            lines.append(f"OAuth 账号: {auth_info['active']}/{auth_info['total']} 可用")
            for provider in auth_info.get("providers", []):
                lines.append(
                    f"- {provider['name']}: {provider['active']}/{provider['total']}"
                )

    elif stats_type == "today":
        lines.append(data.get("title", "📅 今日使用统计"))
        lines.append("")
        lines.append(f"日期: {data.get('subtitle', '')}")
        lines.append(f"- 请求数: {data.get('today_requests', 0)}")
        lines.append(f"- Token: {data.get('today_tokens', '0')}")
        lines.append(f"- 成功率: {data.get('success_rate', 100)}%")
        token_breakdown = data.get("token_breakdown") or {}
        lines.append("")
        lines.append("Token 分解")
        lines.append(f"- 输入: {token_breakdown.get('input', '0')}")
        lines.append(f"- 输出: {token_breakdown.get('output', '0')}")
        lines.append(f"- 推理: {token_breakdown.get('reasoning', '0')}")
        lines.append(f"- 缓存: {token_breakdown.get('cached', '0')}")
        model_stats = data.get("model_stats")
        lines.append("")
        lines.append("模型统计")
        if model_stats:
            for model in model_stats[:10]:
                fail_info = (
                    f" (失败 {model['failed']})" if model.get("failed", 0) > 0 else ""
                )
                lines.append(
                    f"- {model['name']}: {model['requests']} 次{fail_info} / {model['tokens']}"
                )
        else:
            lines.append("- 暂无模型数据")
        time_slots = data.get("time_slots")
        lines.append("")
        lines.append("时段分布")
        if time_slots:
            for slot in time_slots:
                lines.append(f"- {slot['label']}: {slot['count']}")
        else:
            lines.append("- 暂无时段数据")
        auth_stats = data.get("auth_stats")
        lines.append("")
        lines.append("凭证统计")
        if auth_stats:
            for auth in auth_stats[:10]:
                fail_info = (
                    f" | 失败 {auth['failed']}" if auth.get("failed", 0) > 0 else ""
                )
                lines.append(
                    f"- {auth['auth_index']}: {auth['requests']} 次 / {auth['tokens']}{fail_info}"
                )
        else:
            lines.append("- 暂无凭证统计")

    elif stats_type == "quota":
        empty_state = data.get("empty_state")
        if empty_state == "no_accounts":
            return "📭 暂无 OAuth 账号"
        if empty_state == "no_supported_accounts":
            supported_names = ", ".join(data.get("supported_provider_names", []))
            return f"📭 暂无支持配额查询的账号（支持: {supported_names}）"

        lines.append(data.get("title", "📊 OAuth 配额状态"))
        lines.append("")
        accounts = data.get("accounts", [])
        subtitle = data.get("subtitle", "")
        if subtitle:
            lines.append(f"账号概览: {subtitle}")
            lines.append("")
        provider_order = data.get("provider_groups", [])
        grouped_accounts: Dict[str, List[Dict[str, Any]]] = {
            provider: [] for provider in provider_order
        }
        for account in accounts:
            grouped_accounts.setdefault(account.get("provider", "unknown"), []).append(
                account
            )

        for provider in provider_order:
            provider_accounts = grouped_accounts.get(provider, [])
            if not provider_accounts:
                continue
            provider_name = provider_accounts[0].get("provider_name", provider.title())
            provider_icon = provider_accounts[0].get("provider_icon", "📦")
            provider_total = len(provider_accounts)
            display_counts: Dict[str, int] = {}
            for account in provider_accounts:
                display = account.get("email", "未知账号")
                display_counts[display] = display_counts.get(display, 0) + 1
            config_key = "gemini-cli" if provider == "gemini" else provider
            max_count = data.get("max_render_count", {}).get(config_key, 0)
            truncated_count = 0
            if max_count > 0 and len(provider_accounts) > max_count:
                truncated_count = len(provider_accounts) - max_count
                provider_accounts = provider_accounts[:max_count]

            lines.append(f"━━━ {provider_icon} {provider_name}（{provider_total}）━━━")
            for account in provider_accounts:
                lines.append(_build_quota_account_title(account, display_counts))
                if account.get("error"):
                    lines.append(f"   ⚠️ {account['error']}")
                elif account.get("quotas"):
                    for quota in account["quotas"]:
                        lines.append(
                            f"   - {quota['icon']} {quota['label']} {quota['percent']}% · 刷新 {quota['reset_time']}"
                        )
                else:
                    lines.append("   ⚠️ 暂无配额信息")
                lines.append("")

            if truncated_count > 0:
                lines.append(f"⋯ 还有 {truncated_count} 个 {provider_name} 账号未显示")
                lines.append("")

        if not accounts:
            lines.append("📭 暂无支持配额查询的账号")
        lines.append("💡 配额每日自动刷新，百分比为剩余额度")

    elif stats_type == "dashboard":
        today_data = data.get("today") or {}
        quota_data = data.get("quota") or {}
        lines.append("📊 CLIProxyAPI 综合概览")
        lines.append("")
        lines.append("今日摘要")
        lines.append(f"- 日期: {today_data.get('subtitle', '')}")
        lines.append(f"- 请求数: {today_data.get('today_requests', 0)}")
        lines.append(f"- Token: {today_data.get('today_tokens', '0')}")
        lines.append(f"- 成功率: {today_data.get('success_rate', 100)}%")
        lines.append("")
        lines.append("配额摘要")
        quota_empty_state = quota_data.get("empty_state")
        quota_accounts = quota_data.get("accounts", [])
        if not quota_data:
            lines.append("- 暂无配额数据")
        elif quota_empty_state == "no_accounts":
            lines.append("- 暂无 OAuth 账号")
        elif quota_empty_state == "no_supported_accounts":
            lines.append("- 暂无支持配额查询的账号")
        elif not quota_accounts:
            lines.append("- 只有 today 数据，暂无 quota 数据")
        else:
            provider_order = quota_data.get("provider_groups", [])
            grouped_accounts = {provider: [] for provider in provider_order}
            for account in quota_accounts:
                grouped_accounts.setdefault(
                    account.get("provider", "unknown"), []
                ).append(account)
            for provider in provider_order:
                provider_accounts = grouped_accounts.get(provider, [])
                if not provider_accounts:
                    continue
                provider_name = provider_accounts[0].get(
                    "provider_name", provider.title()
                )
                provider_icon = provider_accounts[0].get("provider_icon", "📦")
                lines.append(f"- {provider_icon} {provider_name}")
                summary_accounts = provider_accounts[:2]
                for account in summary_accounts:
                    if account.get("error"):
                        lines.append(
                            f"  {account.get('icon', '•')} {account.get('email', '未知账号')}: {account['error']}"
                        )
                        continue
                    quotas = account.get("quotas", [])
                    if not quotas:
                        lines.append(
                            f"  {account.get('icon', '•')} {account.get('email', '未知账号')}: 暂无配额信息"
                        )
                        continue
                    urgent_quotas = [
                        quota for quota in quotas if quota.get("percent", 100) < 80
                    ][:2]
                    shown_quotas = urgent_quotas or quotas[:1]
                    quota_text = " / ".join(
                        f"{quota['icon']} {quota['label']} {quota['percent']}%"
                        for quota in shown_quotas
                    )
                    lines.append(
                        f"  {account.get('icon', '•')} {account.get('email', '未知账号')}: {quota_text}"
                    )
                if len(provider_accounts) > len(summary_accounts):
                    lines.append(
                        f"  ⋯ 还有 {len(provider_accounts) - len(summary_accounts)} 个账号未展开"
                    )

        analysis = data.get("analysis", "")
        if analysis:
            lines.append("")
            lines.append("LLM 分析")
            lines.append(analysis)

    return "\n".join(lines).rstrip() if lines else None


def build_analysis_report(today_data: Dict[str, Any], analysis: str) -> str:
    report = "📊 **CLIProxyAPI 今日使用分析**\n"
    report += f"📅 日期: {today_data.get('subtitle', '')}\n"
    report += f"📈 请求: {today_data.get('today_requests', 0)} 次 | Token: {today_data.get('today_tokens', '0')}\n"
    report += f"\n{analysis}"
    return report


def build_provider_list_text(providers: List[Dict[str, str]]) -> str:
    lines = ["📋 **可用的 LLM 服务商**", ""]
    lines.append("将以下 ID 填入插件配置的 `llm_provider_id` 字段：")
    lines.append("")
    for index, provider in enumerate(providers, 1):
        lines.append(f"  {index}. `{provider['id']}`")
        if provider.get("name") and provider["name"] != provider["id"]:
            lines.append(f"     └─ {provider['name']}")
    lines.append("")
    lines.append("💡 留空则使用当前对话模型")
    return "\n".join(lines)
