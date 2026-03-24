# CLIProxyAPI Plugin Restructure Design

**Date:** 2026-03-24

## Goal

在不回退现有纯文本功能的前提下，把当前几乎全部塞在 `main.py` 的 AstrBot 插件逻辑拆成更合理的 Python 模块结构，并顺势移除已经退役的图片渲染能力。

## Confirmed Constraints

- AstrBot 插件入口继续保留在 `main.py`
- 现有命令行为保持兼容：`/cpa`、`/cpa today`、`/cpa今日`、`/cpa额度`、`/cpa总览`、`/cpa分析`、`/cpa服务商`
- 当前纯文本输出语义不回退，不恢复图片分支
- `_build_quota_data()` 仍然是 quota 数据构建的唯一主入口，不能回退到重复远端请求的旧逻辑
- `high_res_render` 不允许被重新加回配置
- 本地验证统一使用 `./.venv/bin/python`
- 用户要求中文总结
- 仓库当前没有测试框架，因此先用编译检查和最小行为保持的方式推进

## Structural Direction

采用“保留 `main.py` 作为 AstrBot facade + 根目录扁平模块拆分”的方案。

这样做的理由：

- 改动边界清晰，兼容 AstrBot 当前入口方式
- 符合仓库当前平铺结构和 `AGENTS.md` 的约束
- 可以先完成职责分离，再决定未来是否继续包化
- 与“移除图片渲染能力”结合时风险最可控

## Target File Layout

- `main.py`
  - 只保留插件入口、配置读取、命令注册、少量流程编排、生命周期管理
- `constants.py`
  - API URL、请求头、provider 信息、支持的 quota provider、LLM prompt 模板
- `client.py`
  - `CPAClient`
  - `extract_project_from_filename()`
  - 各种远端调用细节
- `quota_parser.py`
  - Google / GeminiCLI / Codex quota 解析
  - quota 刷新时间格式化
- `builders.py`
  - `build_overview_data()`
  - `build_today_data()`
  - `build_quota_data()`
- `text_renderer.py`
  - `build_text_from_data()`
- `llm_analysis.py`
  - LLM provider 选择辅助
  - 分析 prompt 组装
  - `generate_llm_analysis()`

## Data Flow

### Overview / Today

`main.py` 负责命令入口和 client 获取，调用 `builders.py` 产出结构化数据，再交给 `text_renderer.py` 输出文本。

### Quota

`builders.py` 内部通过 `client.py` 获取 auth 和 quota 原始数据，再通过 `quota_parser.py` 转成统一 quota 结构，最后由 `text_renderer.py` 输出文本。`main.py` 只保留编排，不直接处理 quota 解析细节。

为了保持“quota 数据构建单入口”这一约束，`main.py` 中可以保留一个很薄的 `_build_quota_data()` 包装方法，但它只做模块转发，不再承载任何真实构建逻辑。实际构建逻辑统一收口在 `builders.py` 的 `build_quota_data()`。

### Dashboard + LLM

`main.py` 负责拿到 `today_data` 和 `quota_data`，然后调用 `llm_analysis.py` 生成可选分析文本，再把最终 dashboard 数据交给 `text_renderer.py`。

### Analysis / Providers

`/cpa分析` 的报告拼装也纳入模块化范围：分析正文生成由 `llm_analysis.py` 负责，最终完整文本报告由 `text_renderer.py` 负责或由其提供辅助函数，避免 `main.py` 继续持有大段文本模板。`/cpa服务商` 的 provider 列表格式化同样收口到 `text_renderer.py`，`main.py` 只负责获取 provider 元数据并返回文本。

## Dependency Boundaries

为避免循环依赖，模块依赖方向固定为：

- `constants.py`：不依赖其他业务模块
- `client.py`：只依赖 `constants.py`
- `quota_parser.py`：只依赖标准库，必要时依赖 `constants.py`
- `builders.py`：依赖 `constants.py`、`quota_parser.py`、`client.py`
- `llm_analysis.py`：依赖 `constants.py`，消费 `today_data` / `quota_data`
- `text_renderer.py`：只消费普通数据 dict，不反向依赖 builders 或 main
- `main.py`：位于最外层，只依赖上述模块

特别约束：

- `builders.py` 不导入 `text_renderer.py`
- `text_renderer.py` 不导入 `builders.py`
- `llm_analysis.py` 不直接触发 HTTP quota 拉取

## Removal Scope

这轮结构重构同时纳入“删除已经退役的图片渲染能力”：

- 删除 `stats_renderer.py`
- 从 `requirements.txt` 移除 `Pillow`
- 不保留 `_render_image()`、`event.image_result(...)`、`self._renderer`、`high_res_render` 一类历史路径
- 同步更新 `README.md`、`AGENTS.md` 等文档，去掉“历史遗留图片模块”的说法，改为已移除状态
- 如仓库中仍有图片输出相关配置或说明残留，也一并清理，包括 `_conf_schema.json` 中的历史配置引用检查

## Compatibility Strategy

- 插件入口不变：AstrBot 仍从 `main.py` 加载
- 命令名和配置键尽量不变
- 文本输出以“保持现有语义”为主，不在本轮顺手重写展示结构
- 如需做轻微文案调整，只允许为了模块抽离或删除图片能力而进行

## Verification Strategy

由于本轮会删除 `stats_renderer.py`，验证命令也同步切换到现状：

- `./.venv/bin/python -m py_compile main.py constants.py client.py quota_parser.py builders.py text_renderer.py llm_analysis.py`
- `./.venv/bin/python -m compileall .`

如果中间某一轮尚未创建完全部模块，则按当时实际文件集合执行 `py_compile`。

## Implementation Order

1. 抽 `constants.py`、`client.py`、`quota_parser.py`
2. 抽 `builders.py`、`text_renderer.py`、`llm_analysis.py`
3. 收口 `main.py`，把它变成薄入口
4. 删除 `stats_renderer.py` 和 `Pillow`
5. 同步更新文档和说明
6. 每一轮后用 `./.venv/bin/python` 做编译验证

## Non-Goals For This Round

- 不引入新的自动化测试框架
- 不改 AstrBot 插件装载方式
- 不继续做更激进的包结构改造
- 不顺手做与当前目标无关的大规模文案或风格调整
