"""
CLIProxyAPI 额度与使用统计查询插件
支持查看 OAuth 模型额度和当日调用统计
输出统一为纯文本消息
支持 LLM 智能分析使用情况
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from astrbot.api import AstrBotConfig, logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star

try:
    from .builders import build_overview_data, build_quota_data, build_today_data
    from .client import CPAClient
    from .llm_analysis import (
        generate_llm_analysis,
        get_available_providers,
        get_llm_provider,
    )
    from .text_renderer import (
        build_analysis_report,
        build_provider_list_text,
        build_text_from_data,
    )
except ImportError:
    from builders import build_overview_data, build_quota_data, build_today_data
    from client import CPAClient
    from llm_analysis import (
        generate_llm_analysis,
        get_available_providers,
        get_llm_provider,
    )
    from text_renderer import (
        build_analysis_report,
        build_provider_list_text,
        build_text_from_data,
    )


class Main(Star):
    """CLIProxyAPI 额度统计插件"""

    def __init__(self, context: Context, config: AstrBotConfig) -> None:
        super().__init__(context)
        self.config = config
        self.cpa_url = self.config.get("cpa_url", "")
        self.cpa_password = self.config.get("cpa_password", "")
        self.verify_ssl = self.config.get("verify_ssl", False)
        self.enable_llm_analysis = self.config.get("enable_llm_analysis", False)
        self.llm_provider_id = self.config.get("llm_provider_id", "")
        self.max_render_count: Dict[str, int] = {
            "antigravity": int(self.config.get("max_render_antigravity", 10) or 10),
            "gemini-cli": int(self.config.get("max_render_gemini_cli", 10) or 10),
            "codex": int(self.config.get("max_render_codex", 10) or 10),
        }
        logger.info(f"max_render_count 配置: {self.max_render_count}")
        self._client: Optional[CPAClient] = None

    def _get_client(self) -> Optional[CPAClient]:
        if not self.cpa_url or not self.cpa_password:
            return None
        if self._client is None:
            self._client = CPAClient(self.cpa_url, self.cpa_password, self.verify_ssl)
        return self._client

    def _build_text_from_data(self, data: Dict[str, Any]) -> Optional[str]:
        return build_text_from_data(data)

    async def _build_overview_data(self, client: CPAClient) -> Optional[Dict[str, Any]]:
        return await build_overview_data(client)

    async def _build_today_data(self, client: CPAClient) -> Optional[Dict[str, Any]]:
        return await build_today_data(client)

    async def _build_quota_data(self, client: CPAClient) -> Optional[Dict[str, Any]]:
        return await build_quota_data(client, self.max_render_count, logger.debug)

    def _get_llm_provider(self):
        return get_llm_provider(
            self.context, self.enable_llm_analysis, self.llm_provider_id
        )

    def _get_available_providers(self) -> List[Dict[str, str]]:
        return get_available_providers(self.context)

    async def _generate_llm_analysis(
        self, today_data: Dict[str, Any], quota_data: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        return await generate_llm_analysis(
            self.context,
            self.enable_llm_analysis,
            self.llm_provider_id,
            today_data,
            quota_data,
        )

    async def _get_overview(self, client: CPAClient) -> str:
        data = await self._build_overview_data(client)
        if not data:
            return "❌ 获取使用统计失败，请检查配置"
        return self._build_text_from_data(data) or "❌ 数据格式化失败"

    async def _get_today_stats(self, client: CPAClient) -> str:
        data = await self._build_today_data(client)
        if not data:
            return "❌ 获取使用统计失败，请检查配置"
        return self._build_text_from_data(data) or "❌ 数据格式化失败"

    async def _get_quota_status(self, client: CPAClient) -> str:
        data = await self._build_quota_data(client)
        if not data:
            return "❌ 获取账号状态失败，请检查配置"
        return self._build_text_from_data(data) or "❌ 数据格式化失败"

    @filter.command("cpa")
    async def cpa_stats(self, event: AstrMessageEvent):
        """
        查看 CLIProxyAPI 使用统计
        用法: /cpa [today|总览]
        - /cpa 或 /cpa 总览: 查看总体统计和账号状态
        - /cpa today: 查看今日详细统计
        """
        client = self._get_client()
        if not client:
            yield event.plain_result(
                "❌ 未配置 CLIProxyAPI 地址或密码，请在插件配置中设置"
            )
            return

        args = (
            event.message_str.strip().split()[1:]
            if len(event.message_str.strip().split()) > 1
            else []
        )
        subcommand = args[0].lower() if args else "overview"

        if subcommand in ["today", "今日", "今天"]:
            yield event.plain_result(await self._get_today_stats(client))
        else:
            yield event.plain_result(await self._get_overview(client))

    @filter.command("cpa额度")
    async def cpa_quota(self, event: AstrMessageEvent):
        """查看 CLIProxyAPI OAuth 账号配额（实时获取）"""
        client = self._get_client()
        if not client:
            yield event.plain_result(
                "❌ 未配置 CLIProxyAPI 地址或密码，请在插件配置中设置"
            )
            return

        yield event.plain_result(await self._get_quota_status(client))

    @filter.command("cpa今日")
    async def cpa_today(self, event: AstrMessageEvent):
        """查看今日使用统计"""
        client = self._get_client()
        if not client:
            yield event.plain_result(
                "❌ 未配置 CLIProxyAPI 地址或密码，请在插件配置中设置"
            )
            return

        yield event.plain_result(await self._get_today_stats(client))

    @filter.command("cpa总览")
    async def cpa_dashboard(self, event: AstrMessageEvent):
        """查看综合仪表盘（整合今日统计 + 配额状态 + AI分析）"""
        client = self._get_client()
        if not client:
            yield event.plain_result(
                "❌ 未配置 CLIProxyAPI 地址或密码，请在插件配置中设置"
            )
            return

        yield event.plain_result("📊 正在生成综合仪表盘，请稍候...")

        today_data = await self._build_today_data(client)
        quota_data = await self._build_quota_data(client)
        analysis_text = ""
        if self.enable_llm_analysis and today_data:
            analysis_text = (
                await self._generate_llm_analysis(today_data, quota_data) or ""
            )

        if not today_data:
            yield event.plain_result("❌ 获取使用数据失败")
            return

        dashboard_data = {
            "stats_type": "dashboard",
            "today": today_data,
            "quota": quota_data or {},
            "analysis": analysis_text,
            "query_time": datetime.now().strftime("%H:%M:%S"),
        }
        yield event.plain_result(
            self._build_text_from_data(dashboard_data) or "❌ 数据格式化失败"
        )

    @filter.command("cpa分析")
    async def cpa_analysis(self, event: AstrMessageEvent):
        """查看今日使用情况的 LLM 智能分析"""
        if not self.enable_llm_analysis:
            yield event.plain_result(
                "❌ LLM 分析功能未启用，请在插件配置中开启 'enable_llm_analysis'"
            )
            return

        client = self._get_client()
        if not client:
            yield event.plain_result(
                "❌ 未配置 CLIProxyAPI 地址或密码，请在插件配置中设置"
            )
            return

        yield event.plain_result("🔍 正在分析今日使用情况，请稍候...")

        today_data = await self._build_today_data(client)
        quota_data = await self._build_quota_data(client)
        if not today_data:
            yield event.plain_result("❌ 获取使用数据失败")
            return

        analysis = await self._generate_llm_analysis(today_data, quota_data)
        if analysis:
            yield event.plain_result(build_analysis_report(today_data, analysis))
        else:
            yield event.plain_result("❌ LLM 分析生成失败，请检查 Provider 配置")

    @filter.command("cpa服务商")
    async def cpa_providers(self, event: AstrMessageEvent):
        """列出可用的 LLM 服务商（用于配置 llm_provider_id）"""
        providers = self._get_available_providers()
        if not providers:
            yield event.plain_result(
                "❌ 未找到可用的 LLM 服务商，请先在 AstrBot 中配置提供商"
            )
            return

        yield event.plain_result(build_provider_list_text(providers))

    async def terminate(self):
        """插件终止，关闭 HTTP 连接"""
        if self._client:
            await self._client.close()
            self._client = None
        logger.info("CLIProxyAPI 统计插件已终止")
