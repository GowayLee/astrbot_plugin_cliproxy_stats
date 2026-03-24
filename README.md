# AstrBot CLIProxyAPI 统计插件

一个用于查询 [CLIProxyAPI](https://github.com/router-for-me/CLIProxyAPI) 使用统计和配额信息的 AstrBot 插件。

## 功能特性

- 查看 API 使用统计（请求数、Token 用量、成功率等）
- 查看今日详细使用情况（模型统计、Token 分解、时段分布、凭证统计）
- **实时查询 OAuth 账号配额**（剩余百分比、刷新时间）
- 输出统一为文本消息，适合在私聊和群聊里直接阅读
- 已移除图片渲染能力，当前实现仅维护文本输出链路
- 支持多种凭证类型的配额查询：
  - 🚀 **Antigravity** - 反重力账号
  - 💎 **GeminiCLI** - Gemini CLI 账号
  - 🔮 **Codex** - OpenAI Codex 账号

## 安装

1. 在 AstrBot 插件目录下克隆本仓库：
```bash
cd data/plugins
git clone https://github.com/muyouzhi6/astrbot_plugin_cliproxy_stats.git
```

2. 重启 AstrBot 或在管理面板中重载插件

## 配置

在插件配置中设置以下参数：

| 参数 | 说明 |
|------|------|
| `cpa_url` | CLIProxyAPI 服务地址，如 `https://your-cpa-server.com` |
| `cpa_password` | CLIProxyAPI 管理密钥 |
| `verify_ssl` | 是否校验 SSL 证书 |
| `enable_llm_analysis` | 是否启用 `/cpa分析` |
| `llm_provider_id` | LLM 分析使用的服务商 ID，留空则使用当前对话模型 |
| `max_render_antigravity` | 配额文本中最多显示的 Antigravity 账号数 |
| `max_render_gemini_cli` | 配额文本中最多显示的 GeminiCLI 账号数 |
| `max_render_codex` | 配额文本中最多显示的 Codex 账号数 |

## 项目结构

- `main.py`: AstrBot 插件入口、命令注册和轻量编排
- `constants.py`: 静态常量、请求头、provider 信息、LLM prompt
- `client.py`: CLIProxyAPI HTTP 客户端和 quota 拉取逻辑
- `quota_parser.py`: Google / GeminiCLI / Codex quota 解析与时间格式化
- `builders.py`: overview / today / quota 数据构建
- `text_renderer.py`: 纯文本输出拼装
- `llm_analysis.py`: LLM provider 选择和分析生成
- `_conf_schema.json`: 插件配置 schema

## 使用方法

### /cpa - 查看总览统计

显示总体使用统计和 OAuth 账号状态概览。

```text
📊 CLIProxyAPI 统计

总体统计
- 总请求数: 1234
- 成功率: 97.2%
- 成功/失败: 1200 / 34
- 总 Token: 1.50M

各接口统计
- claude-sonnet-4-5: 500 次 / 800K
- gemini-3-pro: 260 次 / 420K

OAuth 账号: 3/4 可用
- Antigravity: 2/2
- GeminiCLI: 1/1
- Codex: 0/1
```

### /cpa today 或 /cpa今日 - 查看今日统计

显示今日的详细使用情况。

```text
📅 今日使用统计

日期: 2026-03-24
- 请求数: 156
- Token: 250K
- 成功率: 96.8%

Token 分解
- 输入: 120K
- 输出: 96K
- 推理: 24K
- 缓存: 10K

模型统计
- claude-sonnet-4-5: 50 次 / 100K
- gemini-3-pro: 30 次 / 50K

时段分布
- 凌晨 0-6: 10
- 上午 6-12: 45
- 下午 12-18: 60
- 晚间 18-24: 41

凭证统计
- auth-01: 80 次 / 140K
- auth-02: 76 次 / 110K | 失败 2
```

### /cpa额度 - 查看配额状态

**实时**查询各 OAuth 账号的模型配额信息，按 provider 分组输出，并支持每个 provider 的显示数量截断。

```text
📊 OAuth 配额状态

账号概览: 🚀 Antigravity (1) | 💎 GeminiCLI (1)

━━━ 🚀 Antigravity（1）━━━
✅ example@gmail.com
   - 🟢 Claude/GPT 86% · 刷新 03/25 00:36
   - 🟡 Gemini 3 Pro 65% · 刷新 03/25 00:12

━━━ 💎 GeminiCLI（1）━━━
✅ another@gmail.com
   - 🟢 gemini-2.5-pro 92% · 刷新 03/25 00:20
   - 🟠 gemini-2.5-flash 45% · 刷新 03/25 00:30

💡 配额每日自动刷新，百分比为剩余额度
```

## 本地联调脚本

为了反复微调 `/cpa额度` 的文本样式，仓库提供了几个直接复用现有模块的本地脚本。统一使用 `./.venv/bin/python` 运行。

### 1. 直接预览真实 `/cpa额度` 文本

```bash
./.venv/bin/python scripts/quota_text_preview.py --cpa-url 127.0.0.1:8317 --cpa-password 123
```

- 支持环境变量：`CPA_URL`、`CPA_PASSWORD`、`CPA_VERIFY_SSL`
- 地址可以直接写成 `127.0.0.1:8317`，脚本会自动补成 `http://...`
- 可选覆盖截断数：`--max-render-antigravity`、`--max-render-gemini-cli`、`--max-render-codex`

### 2. 抓取真实 quota 样本到 JSON

```bash
./.venv/bin/python scripts/quota_snapshot.py --cpa-url 127.0.0.1:8317 --cpa-password 123 --output tmp/quota_snapshot.json
```

- 保存内容包含 `auth_data`、最终 `quota_data` 和逐账号 `raw_quota_results`
- 适合先抓一份真实样本，再离线反复调文本格式

### 3. 离线重渲染已保存的 quota 样本

```bash
./.venv/bin/python scripts/quota_text_from_snapshot.py tmp/quota_snapshot.json --max-render-codex 1
```

- 主要用于观察 provider 分组和截断效果
- 不再请求真实 CPA 服务，适合纯调 `text_renderer.py`

### /cpa总览 - 查看综合概览

整合今日摘要、配额摘要和可选的 LLM 分析。

```text
📊 CLIProxyAPI 综合概览

今日摘要
- 日期: 2026-03-24
- 请求数: 156
- Token: 250K
- 成功率: 96.8%

配额摘要
- 🚀 Antigravity
  ✅ example@gmail.com: 🟡 Gemini 3 Pro 65%
- 💎 GeminiCLI
  ✅ another@gmail.com: 🟠 gemini-2.5-flash 45%

LLM 分析
当前使用集中在上午与下午，Gemini 3 Pro 配额下降较快，建议优先切换到余量更高的模型。
```

#### 配额状态图标说明

| 图标 | 含义 |
|------|------|
| 🟢 | 充足 (>=80%) |
| 🟡 | 正常 (50-80%) |
| 🟠 | 偏低 (20-50%) |
| 🔴 | 紧张 (<20%) |

## 支持的凭证类型

当前支持以下凭证类型的配额查询：

| 类型 | 图标 | 说明 |
|------|------|------|
| Antigravity | 🚀 | 反重力账号（Google Cloud Code） |
| GeminiCLI | 💎 | Gemini CLI 账号（Google Cloud Code） |
| Codex | 🔮 | OpenAI Codex 账号 |

## 支持的模型分组

以下模型分组可用于 Antigravity 和 GeminiCLI 账号：

- **Claude/GPT**: claude-sonnet-4-5-thinking, claude-opus-4-5-thinking, claude-sonnet-4-5, gpt-oss-120b-medium
- **Gemini 3 Pro**: gemini-3-pro-high, gemini-3-pro-low
- **Gemini 2.5 Flash**: gemini-2.5-flash, gemini-2.5-flash-thinking
- **Gemini 2.5 Flash Lite**: gemini-2.5-flash-lite
- **Gemini 2.5 CU**: rev19-uic3-1p
- **Gemini 3 Flash**: gemini-3-flash
- **Gemini 3 Pro Image**: gemini-3-pro-image

## 依赖

- AstrBot >= 3.0
- aiohttp

## 许可证

MIT License

## 作者

木有知

## 相关链接

- [CLIProxyAPI](https://github.com/router-for-me/CLIProxyAPI) - CLI Proxy API 服务端
- [AstrBot](https://github.com/Soulter/AstrBot) - 多平台 LLM 聊天机器人框架
