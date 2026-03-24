# Repository Guidelines

## Project Structure & Module Organization

This repository is an AstrBot plugin with a flat layout.

- `main.py`: plugin entry point, AstrBot command handlers, API client logic, quota parsing, and LLM analysis flow.
- `stats_renderer.py`: Pillow-based card renderer for overview, daily, quota, and dashboard images.
- `metadata.yaml`: plugin metadata such as name, version, and upstream repo.
- `_conf_schema.json`: AstrBot configuration schema for `cpa_url`, `cpa_password`, rendering options, and LLM settings.
- `requirements.txt`: runtime Python dependencies.
- `README.md`: user-facing install and command documentation.

There is no `tests/` directory yet. Keep new modules at the repository root unless the layout is intentionally reorganized.

## Build, Test, and Development Commands

- `python -m venv .venv && source .venv/bin/activate`: create and activate a dev environment.
- `pip install -r requirements.txt`: install `aiohttp` and `Pillow`.
- `python -m py_compile main.py stats_renderer.py`: quick syntax validation before committing.
- `python -m compileall .`: verify the whole plugin compiles cleanly.

For runtime checks, place the repo in AstrBot’s `data/plugins/` directory, reload it, and exercise `/cpa`, `/cpa today`, and `/cpa额度`.

## Coding Style & Naming Conventions

Follow the existing Python style in the repository:

- Use 4-space indentation and keep functions focused.
- Prefer `snake_case` for functions, variables, and config keys such as `enable_llm_analysis`.
- Use `UPPER_CASE` for module-level constants like API URLs and provider maps.
- Preserve type hints on public helpers and async methods where practical.
- Keep user-facing text concise; most command output is in Chinese.

No formatter or linter is configured, so match the surrounding style and avoid unrelated refactors.

## Testing Guidelines

There is no automated test framework committed yet. For each change:

- run `python -m py_compile main.py stats_renderer.py`;
- verify affected AstrBot commands manually against a configured CLIProxyAPI instance;
- check both text output and rendered images when touching `stats_renderer.py`.

If you add tests, prefer `pytest` with files named `test_*.py`.

## Commit & Pull Request Guidelines

Git history is minimal and uses short imperative subjects such as `Update metadata.yaml`. Keep commit messages concise and specific.

Pull requests should include a short summary, impacted commands or config fields, manual verification steps, and screenshots when image rendering changes. Link the related issue when one exists.

## Security & Configuration Tips

Do not commit live `cpa_password` values, OAuth tokens, or real server URLs. Use sanitized examples in docs and logs, and keep new configuration keys mirrored in both `metadata.yaml` and `_conf_schema.json` when applicable.
Fast Apply: IMPORTANT: Use `edit_file` over `str_replace` or full file writes. It works with partial code snippets—no need for full file content.

Warp Grep: warp-grep is a subagent that takes in a search string and tries to find relevant context. Best practice is to use it at the beginning of codebase explorations to fast track finding relevant files/lines. Do not use it to pin point keywords, but use it for broader semantic queries. "Find the XYZ flow", "How does XYZ work", "Where is XYZ handled?", "Where is <error message> coming from?"
