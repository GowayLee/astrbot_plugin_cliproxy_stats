"""Static configuration for the CLIProxyAPI stats plugin."""

ANTIGRAVITY_QUOTA_URLS = [
    "https://daily-cloudcode-pa.googleapis.com/v1internal:fetchAvailableModels",
    "https://daily-cloudcode-pa.sandbox.googleapis.com/v1internal:fetchAvailableModels",
    "https://cloudcode-pa.googleapis.com/v1internal:fetchAvailableModels",
]

GEMINI_CLI_QUOTA_URL = (
    "https://cloudcode-pa.googleapis.com/v1internal:retrieveUserQuota"
)

GEMINI_CLI_QUOTA_HEADERS = {
    "Authorization": "Bearer $TOKEN$",
    "Content-Type": "application/json",
}

ANTIGRAVITY_REQUEST_HEADERS = {
    "Authorization": "Bearer $TOKEN$",
    "Content-Type": "application/json",
    "User-Agent": "antigravity/1.11.5 windows/amd64",
}

GEMINI_CLI_REQUEST_HEADERS = {
    "Authorization": "Bearer $TOKEN$",
    "Content-Type": "application/json",
    "User-Agent": "google-api-nodejs-client/9.15.1",
    "X-Goog-Api-Client": "gl-node/22.17.0",
    "Client-Metadata": "ideType=IDE_UNSPECIFIED,platform=PLATFORM_UNSPECIFIED,pluginType=GEMINI",
}

CODEX_QUOTA_URL = "https://chatgpt.com/backend-api/wham/usage"
CODEX_QUOTA_HEADERS = {
    "Authorization": "Bearer $TOKEN$",
    "Content-Type": "application/json",
}

QUOTA_SUPPORTED_PROVIDERS = ["antigravity", "gemini", "gemini-cli", "codex"]

PROVIDER_INFO = {
    "antigravity": {
        "name": "Antigravity",
        "icon": "🚀",
        "color": "#8b5cf6",
        "supports_quota": True,
    },
    "gemini": {
        "name": "GeminiCLI",
        "icon": "💎",
        "color": "#3b82f6",
        "supports_quota": True,
    },
    "gemini-cli": {
        "name": "GeminiCLI",
        "icon": "💎",
        "color": "#3b82f6",
        "supports_quota": True,
    },
    "claude": {
        "name": "Claude",
        "icon": "🤖",
        "color": "#f59e0b",
        "supports_quota": False,
    },
    "codex": {
        "name": "Codex",
        "icon": "🔮",
        "color": "#10b981",
        "supports_quota": True,
    },
    "iflow": {
        "name": "iFlow",
        "icon": "🌊",
        "color": "#06b6d4",
        "supports_quota": False,
    },
    "qwen": {
        "name": "Qwen",
        "icon": "🌙",
        "color": "#ec4899",
        "supports_quota": False,
    },
}

LLM_ANALYSIS_PROMPT = """你是一个 API 使用分析专家。请根据以下 CLIProxyAPI 使用数据，提供精准的分析报告。

## 当前时间
{current_time}

## 今日使用数据
- 日期: {date}
- 总请求数: {total_requests}
- 总 Token: {total_tokens}
- 成功率: {success_rate}%
- 已运行时长: 从 00:00 到现在约 {hours_elapsed} 小时

## 各模型使用详情
{model_stats}

## 配额状态（含刷新时间）
{quota_stats}

## 小时级使用分布
{hourly_distribution}

请提供以下分析：

### 1. 配额安全评估（最重要）
对于每个配额紧张的模型（剩余 < 80%）：
- 计算：当前消耗速率 = 已用配额 / 已运行小时数
- 计算：预计耗尽时间 = 剩余配额 / 消耗速率
- **关键判断**：在该模型的刷新时间之前，配额是否会耗尽？
  - 如果刷新时间在耗尽之前 → ✅ 安全，无需担心
  - 如果耗尽在刷新之前 → ⚠️ 预警，给出预计耗尽时间
- 配额充足（> 80%）的模型不需要预警

### 2. 模型使用分析
- 哪个模型是主力？占比多少？
- 各模型的平均单次 Token 消耗
- 是否有异常高消耗的模型？

### 3. 优化建议（仅在必要时给出）
- **只有当配额确实会在刷新前耗尽时**，才建议切换模型
- 如果配额安全，明确说"当前使用模式可持续，无需调整"
- 不要为了建议而建议

请用中文回答，数据要准确，结论要明确。"""
