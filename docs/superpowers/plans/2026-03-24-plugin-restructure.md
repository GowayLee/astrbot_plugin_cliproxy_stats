# CLIProxyAPI Plugin Restructure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在保持现有纯文本功能兼容的前提下，把 `main.py` 拆成职责清晰的模块，并删除已经退役的图片渲染能力。

**Architecture:** 保留 `main.py` 作为 AstrBot 插件入口和轻量编排层，把常量、HTTP client、quota 解析、数据构建、文本渲染和 LLM 分析分别拆到根目录新模块。重构完成后删除 `stats_renderer.py` 和 `Pillow`，让仓库结构与当前纯文本实现保持一致。

**Tech Stack:** Python, AstrBot plugin API, aiohttp, local venv at `./.venv`

---

## File Map

- Create: `constants.py`
- Create: `client.py`
- Create: `quota_parser.py`
- Create: `builders.py`
- Create: `text_renderer.py`
- Create: `llm_analysis.py`
- Modify: `main.py`
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `requirements.txt`
- Modify: `_conf_schema.json`
- Delete: `stats_renderer.py`
- Reference: `_conf_schema.json`
- Reference: `metadata.yaml`
- Reference: `docs/superpowers/specs/2026-03-24-plugin-restructure-design.md`

### Task 1: 抽出常量和远端调用层

**Files:**
- Create: `constants.py`
- Create: `client.py`
- Modify: `main.py`

- [ ] **Step 1: 在 `constants.py` 定义静态常量**

把以下内容从 `main.py` 迁出并保持命名稳定：

- 各类 quota URL
- 请求头模板
- `QUOTA_SUPPORTED_PROVIDERS`
- `PROVIDER_INFO`
- `LLM_ANALYSIS_PROMPT`

- [ ] **Step 2: 在 `client.py` 新建 `extract_project_from_filename()`**

把 GeminiCLI project 提取逻辑迁入 `client.py`，不改输入输出语义。

- [ ] **Step 3: 在 `client.py` 新建 `CPAClient`**

迁移：

- `_get_headers()`
- `_get_session()`
- `close()`
- `get_usage()`
- `get_auth_files()`
- `api_call()`
- `get_gemini_cli_quota()`
- `get_google_quota()`
- `get_codex_quota()`

- [ ] **Step 4: 在 `main.py` 改成从新模块导入**

保留 `self._client` 的复用策略和原有配置读取方式。

- [ ] **Step 5: 运行编译检查**

Run: `./.venv/bin/python -m py_compile main.py constants.py client.py`

Expected:
- PASS

### Task 2: 抽出 quota 解析层

**Files:**
- Create: `quota_parser.py`
- Modify: `main.py`

- [ ] **Step 1: 在 `quota_parser.py` 新建时间格式化 helper**

迁移：

- `_format_reset_time()`
- `_format_codex_reset_time()`

- [ ] **Step 2: 在 `quota_parser.py` 新建 quota 解析函数**

迁移并整理：

- `_parse_quota_dynamic()`
- `_parse_gemini_cli_quota_dynamic()`
- `_parse_codex_quota()`

只把当前主流程仍然会用到的 parser 作为公开接口。`_parse_quota()`、`_parse_antigravity_quota()`、`_parse_gemini_cli_quota()` 如仅为旧聚合路径保留，应先确认是否仍被使用；未使用则不迁入新模块，避免把历史兼容残留固化成新结构。

- [ ] **Step 3: 统一 quota parser 的公开接口**

明确导出哪些纯函数给 builders 使用，例如：

- `parse_google_quota_dynamic(models)`
- `parse_gemini_cli_quota_dynamic(buckets)`
- `parse_codex_quota(rate_limit, plan_type)`
- `format_reset_time(reset_time)`
- `format_codex_reset_time(reset_at)`

确保 builders 层不再依赖 `main.py` 实例方法。

- [ ] **Step 4: 运行编译检查**

Run: `./.venv/bin/python -m py_compile main.py constants.py client.py quota_parser.py`

Expected:
- PASS

### Task 3: 抽出数据构建层

**Files:**
- Create: `builders.py`
- Modify: `main.py`

- [ ] **Step 1: 在 `builders.py` 新建通用格式化 helper**

迁移：

- `_format_tokens()`
- `_get_provider_display()`

如果需要，把仅供 builders 使用的聚合 helper 一并放入这个模块。

- [ ] **Step 2: 迁移 overview 数据构建**

把 `_build_overview_data()` 改成模块函数，输入保持清晰：

- `client`
- 当前时间来源
- 必要 helper

- [ ] **Step 3: 迁移 today 数据构建**

把 `_build_today_data()` 改成模块函数，保持现有字段：

- `token_breakdown`
- `model_stats`
- `time_slots`
- `auth_stats`

- [ ] **Step 4: 迁移 quota 数据构建**

把 `_build_quota_data()` 改成模块函数，继续保持：

- 按 provider 分组
- 复用 quota parser
- 不重复远端请求
- `max_render_count` 透传给文本层

- [ ] **Step 5: 在 `main.py` 改为调用 builder 模块**

让 `main.py` 不再持有这些大块构建逻辑。

- [ ] **Step 6: 运行编译检查**

Run: `./.venv/bin/python -m py_compile main.py constants.py client.py quota_parser.py builders.py`

Expected:
- PASS

### Task 4: 抽出文本渲染和 LLM 分析层

**Files:**
- Create: `text_renderer.py`
- Create: `llm_analysis.py`
- Modify: `main.py`

- [ ] **Step 1: 在 `text_renderer.py` 新建 `build_text_from_data()`**

迁移 overview / today / quota / dashboard 的文本拼装逻辑，尽量保持当前输出语义稳定。

- [ ] **Step 2: 在 `text_renderer.py` 新建分析与 provider 文本 helper**

迁移或新增：

- `build_analysis_report(today_data, analysis_text)`
- `build_provider_list_text(providers)`

这样 `/cpa分析` 和 `/cpa服务商` 的文本也不再留在 `main.py`。

- [ ] **Step 3: 在 `llm_analysis.py` 新建 provider 相关 helper**

迁移：

- `_get_llm_provider()`
- `_get_available_providers()`

如果需要，把对 `context` 的依赖作为显式参数传入。

- [ ] **Step 4: 在 `llm_analysis.py` 新建 `generate_llm_analysis()`**

迁移 `_generate_llm_analysis()`，保留现有 prompt 组装和 quota/today 数据消费方式。

- [ ] **Step 5: 在 `main.py` 收口成薄入口**

保留：

- 配置读取
- client 获取
- 命令注册
- dashboard 编排
- terminate 生命周期管理

同时明确迁移/删除清单：

- 删除 `_build_text_from_data()` 实现，改为模块调用
- 删除 `_build_overview_data()` / `_build_today_data()` / `_build_quota_data()` 实现，必要时保留仅转发到 builders 的薄包装
- 删除 `_format_tokens()`、`_get_provider_display()`、quota parser 相关实例方法
- 删除 `_get_llm_provider()`、`_get_available_providers()`、`_generate_llm_analysis()` 实现，改为模块调用
- `cpa_analysis()` 和 `cpa_providers()` 只保留命令编排，不保留大段文本模板

- [ ] **Step 6: 运行编译检查**

Run: `./.venv/bin/python -m py_compile main.py constants.py client.py quota_parser.py builders.py text_renderer.py llm_analysis.py`

Expected:
- PASS

### Task 5: 删除图片渲染能力

**Files:**
- Delete: `stats_renderer.py`
- Modify: `requirements.txt`
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `_conf_schema.json`
- Modify: `main.py`

- [ ] **Step 1: 删除 `stats_renderer.py`**

确认主流程和文档中都不再依赖该模块后，直接删掉文件。

- [ ] **Step 2: 从 `requirements.txt` 删除 `Pillow`**

只保留当前纯文本实现仍然需要的依赖。

- [ ] **Step 3: 全仓搜索并清理图片历史路径**

显式确认并清理：

- `_render_image()`
- `event.image_result(...)`
- `self._renderer`
- `high_res_render`
- `StatsCardRenderer`
- 其他图片渲染相关 import / 注释 / 文案

- [ ] **Step 4: 更新 `_conf_schema.json`**

确认没有 `high_res_render` 等历史图片配置残留，也不把它们误加回来。

- [ ] **Step 5: 更新 README**

把涉及图片渲染、历史遗留 renderer 的表述改成“纯文本输出、已移除图片能力”。

- [ ] **Step 6: 更新 AGENTS**

把项目结构、验证说明和渲染相关描述改成最新状态。

- [ ] **Step 7: 运行编译检查**

Run: `./.venv/bin/python -m py_compile main.py constants.py client.py quota_parser.py builders.py text_renderer.py llm_analysis.py`

Expected:
- PASS

### Task 6: 全量验证与收尾

**Files:**
- Modify: `main.py`
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `requirements.txt`

- [ ] **Step 1: 运行全量编译**

Run: `./.venv/bin/python -m compileall .`

Expected:
- PASS

- [ ] **Step 2: 检查 `main.py` 剩余职责**

确认 `main.py` 只保留：

- 插件入口
- 命令注册
- 少量 orchestration
- 生命周期管理

- [ ] **Step 3: 检查插件入口兼容性**

确认 AstrBot 仍然从 `main.py` 加载，入口类名和命令装饰器未被破坏。

- [ ] **Step 4: 检查图片能力已彻底移除**

确认仓库中不再存在：

- `stats_renderer.py`
- `Pillow` 运行时依赖
- 主流程图片分支说明

- [ ] **Step 5: 整理汇报内容**

汇报必须覆盖：

- 新增了哪些模块
- `main.py` 还剩哪些职责
- 插件入口是否变化
- 本轮验证命令和结果

- [ ] **Step 6: 做最小手工 smoke check 清单**

至少人工确认以下运行期行为未被结构重构破坏：

- `/cpa`
- `/cpa today`
- `/cpa今日`
- `/cpa额度`
- `/cpa总览`
- `/cpa分析`
- `/cpa服务商`
- `terminate()` 仍会关闭复用的 client
- quota 仍然通过单入口构建，不回退到重复请求旧逻辑
