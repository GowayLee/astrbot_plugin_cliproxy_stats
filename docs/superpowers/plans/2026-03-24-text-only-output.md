# Text-Only Output Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将插件所有命令从“优先渲染图片，失败回退文本”改为“直接输出文本”，保留现有数据获取、统计、配额解析和 LLM 分析能力。

**Architecture:** 保留现有 `_build_overview_data()`、`_build_today_data()`、`_build_quota_data()` 作为统一数据构建层，把 `main.py` 中所有命令入口统一收敛到文本渲染路径。用 `_build_text_from_data()` 作为核心文本格式化器，并让 quota 文本逻辑复用 build-data 结果，消除重复 API 请求。

**Tech Stack:** Python, AstrBot plugin API, aiohttp, existing CLIProxyAPI client logic

---

## Scope

### Required in this change

- `main.py`
  - 删除所有统计命令中的图片输出分支
  - 让 `overview/today/quota/dashboard` 全部有稳定文本输出
  - 让 quota 文本复用 `_build_quota_data()`，避免重复请求
  - 删除主流程中不再使用的图片 helper / import
- `README.md`
- `_conf_schema.json`
- `metadata.yaml`
- `AGENTS.md`

### Explicitly out of scope for this change

- 删除 `stats_renderer.py`
- 从 `requirements.txt` 移除 `Pillow`
- 引入新的自动化测试框架

这些项作为后续清理任务处理，避免本次“切换输出模式”与“彻底删除图片技术栈”混在一起。

## File Map

- Modify: `main.py`
  - 命令入口：`cpa_stats()`、`cpa_quota()`、`cpa_today()`、`cpa_dashboard()`
  - 文本构建：`_build_text_from_data()`
  - quota 文本复用：`_get_quota_status()`
  - 可选新增：`_get_dashboard_text()`
  - 清理未使用图片路径：`_render_image()`、图片相关 import、`self._renderer`、`self.high_res_render`
- Modify: `README.md`
  - 更新用户说明，从图片输出改为文本输出
- Modify: `_conf_schema.json`
  - 删除或调整图片专属配置描述
- Modify: `metadata.yaml`
  - 更新插件介绍文案
- Modify: `AGENTS.md`
  - 更新开发指引中与图片渲染相关的说明

## Task 1: 先补齐文本输出能力，再切换命令入口

**Files:**
- Modify: `main.py:589`
- Modify: `main.py:1451`
- Modify: `main.py:1458`
- Modify: `main.py:1465`
- Optional create/modify: dashboard text helper in `main.py`

- [ ] **Step 1: 扩展 `today` 文本，纳入现有 build-data 字段**

目标：让 `today` 文本覆盖当前已有数据，而不是只显示请求数和 Token。

必须包含：
- 日期
- 请求数 / Token / 成功率
- `token_breakdown`
- `model_stats`（保留前 10 项）
- `time_slots`
- `auth_stats`（保留前 10 项）

- [ ] **Step 2: 扩展 `quota` 文本，按 provider 分组输出**

目标：让 `_build_text_from_data()` 能直接消费 `_build_quota_data()` 的结果。

必须输出：
- provider 标题，如 `━━━ 🚀 Antigravity ━━━`
- 每个账号的状态和显示名
- 每个 quota 的图标、label、percent、reset_time
- 每个 provider 的截断提示

具体实现要求：
- 使用 `data["accounts"]` 中现有的 `provider/provider_name/provider_icon/error/quotas`
- 不再依赖 `_get_quota_status()` 内部再查一遍远端
- 按 `self.max_render_count` 保留当前文本路径已有的 provider 截断语义

- [ ] **Step 3: 新增 `dashboard` 文本输出**

实现方式二选一，推荐第一种：

1. 在 `_build_text_from_data()` 中增加 `stats_type == "dashboard"`
2. 单独新增 `_get_dashboard_text(dashboard_data)` helper

推荐输出结构：
- 标题：`CLIProxyAPI 综合概览`
- 今日摘要：请求 / Token / 成功率
- 配额摘要：按 provider 展示前若干账号和紧张配额
- LLM 分析：如果 `analysis` 不为空，则原样追加

长度控制：
- dashboard 中的 `model_stats` 不展开全部明细，只显示 today 摘要
- dashboard 中 quota 摘要每个 provider 只显示少量账号，避免刷屏

- [ ] **Step 4: 明确空数据回退文案**

为以下场景补稳定文案：
- `today` 无模型数据
- `today` 无时段数据
- `today` 无凭证统计
- `quota` 无账号
- `quota` 无支持额度查询账号
- `dashboard` 只有 today 没有 quota

- [ ] **Step 5: 让 `_get_overview()` 与 `_get_today_stats()` 只做“build data -> build text”**

目标实现：

```python
data = await self._build_today_data(client)
if not data:
    return "❌ 获取使用统计失败，请检查配置"
return self._build_text_from_data(data) or "❌ 数据格式化失败"
```

- [ ] **Step 6: 重写 `_get_quota_status()`，彻底复用 `_build_quota_data()`**

目标实现：

```python
data = await self._build_quota_data(client)
if not data:
    return "❌ 获取账号状态失败，请检查配置"
return self._build_text_from_data(data) or "❌ 数据格式化失败"
```

额外要求：
- 保留“暂无 OAuth 账号”与“暂无支持配额查询的账号”这两类用户友好提示
- 如果 `_build_quota_data()` 当前无法区分这两类场景，则先补数据层标记，再在文本层处理

- [ ] **Step 7: 运行语法检查，确认新增文本路径可编译**

Run: `python -m py_compile main.py stats_renderer.py`

Expected:
- PASS
- 尚未切命令入口，但文本 helper 已经可用

## Task 2: 切换四个命令入口到纯文本输出

**Files:**
- Modify: `main.py:927`
- Modify: `main.py:964`
- Modify: `main.py:982`
- Modify: `main.py:1000`

- [ ] **Step 1: 修改 `cpa_stats()` 的 today 分支**

将：
- `_build_today_data()`
- `_render_image()`
- `event.image_result()`

替换为：
- `yield event.plain_result(await self._get_today_stats(client))`

要求：
- `/cpa today`
- `/cpa 今日`
- `/cpa 今天`

都走同一套 today 文本 helper。

- [ ] **Step 2: 修改 `cpa_stats()` 的 overview 分支**

将 overview 分支改为：

```python
yield event.plain_result(await self._get_overview(client))
```

- [ ] **Step 3: 修改 `cpa_quota()`**

将 quota 命令改为：

```python
yield event.plain_result(await self._get_quota_status(client))
```

不再调用：
- `_build_quota_data()`
- `_render_image()`
- `event.image_result()`

- [ ] **Step 4: 修改 `cpa_today()`**

将 today 专用命令改为：

```python
yield event.plain_result(await self._get_today_stats(client))
```

要求：
- 与 `/cpa today` 输出完全共享同一 helper
- 不再保留第二套图片分支

- [ ] **Step 5: 修改 `cpa_dashboard()`**

保留：
- client 配置检查
- `📊 正在生成综合仪表盘，请稍候...`
- today/quota/analysis 的数据构建顺序

替换最终输出为：

```python
yield event.plain_result(self._build_text_from_data(dashboard_data) or "❌ 数据格式化失败")
```

或使用 Task 1 中新增的 `_get_dashboard_text()`。

- [ ] **Step 6: 检查 `event.image_result(...)` 是否已从统计命令全部消失**

需要覆盖的命令：
- `cpa_stats`
- `cpa_quota`
- `cpa_today`
- `cpa_dashboard`

- [ ] **Step 7: 再跑一次语法检查**

Run: `python -m py_compile main.py stats_renderer.py`

Expected:
- PASS
- 四个命令入口都已完全转为文本输出

## Task 3: 清理主流程里的图片依赖

**Files:**
- Modify: `main.py:1`
- Modify: `main.py:23`
- Modify: `main.py:26`
- Modify: `main.py:560`
- Modify: `main.py:501`

- [ ] **Step 1: 删除未使用的图片 import**

检查并删除：
- `from .stats_renderer import StatsCardRenderer`
- `from astrbot.core.utils.io import save_temp_img`
- `from astrbot.api.message_components import Image`

前提：确认主流程已无图片输出调用。

- [ ] **Step 2: 删除 `_render_image()` helper**

前提：代码中已没有任何调用点。

删除后再次检查：
- 没有残留 `_render_image(` 引用

- [ ] **Step 3: 删除 `self._renderer` 与 `self.high_res_render`**

目标：
- 从 `__init__` 中移除 `high_res_render` 配置读取
- 从 `__init__` 中移除 `self._renderer`

额外检查：
- 删除后没有未使用变量或类型引用

- [ ] **Step 4: 更新 `main.py` 顶部说明与相关注释**

至少修改：
- 文件头部 docstring 中“输出渲染为现代卡片风格图片”
- 与图片输出相关的函数注释

- [ ] **Step 5: 运行语法检查**

Run: `python -m py_compile main.py stats_renderer.py`

Expected:
- PASS
- `stats_renderer.py` 仍存在，但不再被主流程使用

## Task 4: 同步文档与配置说明

**Files:**
- Modify: `README.md`
- Modify: `_conf_schema.json`
- Modify: `metadata.yaml`
- Modify: `AGENTS.md`

- [ ] **Step 1: 更新 README 用户文案**

必须处理：
- 删除“图片卡片”“渲染图片”相关描述
- 如果 README 展示命令输出，改成文本示例
- 如果 README 提到截图，改成文本展示说明

- [ ] **Step 2: 更新 `_conf_schema.json`**

必须处理：
- 删除 `high_res_render`，因为它只服务图片输出
- 保留 `max_render_antigravity`
- 保留 `max_render_gemini_cli`
- 保留 `max_render_codex`

必须改文案：
- 从“最大渲染数量 / 配额图片中最多显示”
- 改成“文本输出中最多显示的账号数”之类的描述

- [ ] **Step 3: 更新 `metadata.yaml`**

必须处理：
- 插件简介里如果有图片/卡片相关字样，改成文本统计输出

- [ ] **Step 4: 更新 `AGENTS.md`**

必须处理：
- `stats_renderer.py` 的说明改成历史遗留或未使用模块（如果文件仍保留）
- “check both text output and rendered images” 改成只检查文本输出
- “screenshots when image rendering changes” 改成适用于文本输出变化的说明

## Task 5: 手工验证和“无重复 quota 请求”验证

**Files:**
- Modify: `main.py`
- Verify runtime behavior in AstrBot

- [ ] **Step 1: 运行全量编译检查**

Run: `python -m compileall .`

Expected:
- PASS

- [ ] **Step 2: 手工验证五个命令都输出纯文本**

逐个执行：
- `/cpa`
- `/cpa today`
- `/cpa今日`
- `/cpa额度`
- `/cpa总览`

Expected:
- 全部返回文本消息
- 不出现图片消息

- [ ] **Step 3: 验证 today 双入口输出一致**

对比：
- `/cpa today`
- `/cpa今日`

Expected:
- 两者主体内容一致
- 只允许触发词不同，不允许格式漂移

- [ ] **Step 4: 验证 quota provider 截断仍生效**

准备：
- 使用超过 `max_render_*` 上限的账号集合

Expected:
- 每个 provider 只展示上限数量的账号
- 有明确的“还有 N 个账号未显示”提示

- [ ] **Step 5: 验证 quota 不再重复请求远端**

执行方法：
- 在 AstrBot 和/或 CLIProxyAPI 后端开启 debug 日志
- 执行一次 `/cpa额度`
- 观察 `/v0/management/auth-files` 和 `/v0/management/api-call` 的调用次数

Expected:
- 一次命令只出现一轮账号获取和额度查询
- 不再出现“先查一遍用于渲染，失败后再查一遍用于文本”的第二轮请求

- [ ] **Step 6: 验证 dashboard 文本长度可接受**

Expected:
- 有 today 摘要
- 有 quota 摘要
- 若启用 LLM 分析，分析能追加
- 单条消息长度仍适合群聊阅读

- [ ] **Step 7: Commit**

建议提交信息：

```bash
git add main.py README.md _conf_schema.json metadata.yaml AGENTS.md
git commit -m "Switch CPA stats output to text"
```

## Follow-Up Cleanup

这些不属于本轮必做项，但在主功能稳定后可以单独起一轮清理：

- 删除 `stats_renderer.py`
- 从 `requirements.txt` 移除 `Pillow`
- 从仓库说明中彻底移除图片技术栈
