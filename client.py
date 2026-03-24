"""HTTP client for CLIProxyAPI management endpoints."""

import asyncio
import json
import re
from typing import Any, Dict, Optional

import aiohttp
from aiohttp import ClientTimeout

from astrbot.api import logger

from constants import (
    ANTIGRAVITY_QUOTA_URLS,
    ANTIGRAVITY_REQUEST_HEADERS,
    CODEX_QUOTA_HEADERS,
    CODEX_QUOTA_URL,
    GEMINI_CLI_QUOTA_HEADERS,
    GEMINI_CLI_QUOTA_URL,
)


def extract_project_from_filename(filename: str) -> Optional[str]:
    """Extract GeminiCLI project name from credential filename."""
    if not filename:
        return None

    name = filename.rstrip(".json") if filename.endswith(".json") else filename

    match = re.match(r"^gemini-[^@]+@[^-]+-(.+)$", name)
    if match:
        return match.group(1)

    if "@" in name and "-" in name:
        at_pos = name.rfind("@")
        after_at = name[at_pos + 1 :]
        dash_pos = after_at.find("-")
        if dash_pos != -1:
            return after_at[dash_pos + 1 :]

    return None


class CPAClient:
    """CLIProxyAPI client."""

    def __init__(self, base_url: str, password: str, verify_ssl: bool = False):
        self.base_url = base_url.rstrip("/")
        self.password = password
        self.verify_ssl = verify_ssl
        self._session: Optional[aiohttp.ClientSession] = None

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.password}",
            "Content-Type": "application/json",
        }

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            connector = (
                aiohttp.TCPConnector()
                if self.verify_ssl
                else aiohttp.TCPConnector(ssl=False)
            )
            self._session = aiohttp.ClientSession(connector=connector)
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
            await asyncio.sleep(0.25)
        self._session = None

    async def get_usage(self) -> Optional[Dict[str, Any]]:
        url = f"{self.base_url}/v0/management/usage"
        try:
            session = await self._get_session()
            async with session.get(
                url, headers=self._get_headers(), timeout=ClientTimeout(total=30)
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                text = await resp.text()
                logger.error(f"获取 usage 失败: {resp.status} - {text}")
                return None
        except Exception as exc:
            logger.error(f"请求 usage 接口出错: {exc}")
            return None

    async def get_auth_files(self) -> Optional[Dict[str, Any]]:
        url = f"{self.base_url}/v0/management/auth-files"
        try:
            session = await self._get_session()
            async with session.get(
                url, headers=self._get_headers(), timeout=ClientTimeout(total=30)
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                text = await resp.text()
                logger.error(f"获取 auth-files 失败: {resp.status} - {text}")
                return None
        except Exception as exc:
            logger.error(f"请求 auth-files 接口出错: {exc}")
            return None

    async def api_call(
        self,
        auth_index: str,
        method: str,
        url: str,
        header: Dict[str, str],
        data: str = "",
    ) -> Optional[Dict[str, Any]]:
        api_url = f"{self.base_url}/v0/management/api-call"
        payload = {
            "auth_index": auth_index,
            "method": method,
            "url": url,
            "header": header,
            "data": data,
        }
        try:
            session = await self._get_session()
            async with session.post(
                api_url,
                headers=self._get_headers(),
                json=payload,
                timeout=ClientTimeout(total=60),
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    if "body" in result and isinstance(result["body"], str):
                        try:
                            result["body"] = json.loads(result["body"])
                        except (json.JSONDecodeError, TypeError):
                            pass
                    return result
                text = await resp.text()
                logger.error(f"api-call 失败: {resp.status} - {text}")
                return None
        except Exception as exc:
            logger.error(f"api-call 请求出错: {exc}")
            return None

    async def get_antigravity_quota(self, auth_index: str) -> Dict[str, Any]:
        return await self.get_google_quota(auth_index, "antigravity")

    async def get_gemini_cli_quota(
        self, auth_index: str, project: str
    ) -> Dict[str, Any]:
        if not project:
            return {"success": False, "error": "无法提取项目名称", "error_code": 0}

        result = await self.api_call(
            auth_index=auth_index,
            method="POST",
            url=GEMINI_CLI_QUOTA_URL,
            header=GEMINI_CLI_QUOTA_HEADERS,
            data=json.dumps({"project": project}),
        )

        if result:
            status_code = result.get("status_code", 0)
            if status_code == 200:
                body = result.get("body", {})
                if isinstance(body, str):
                    try:
                        body = json.loads(body)
                    except json.JSONDecodeError:
                        body = {}
                if isinstance(body, dict) and "buckets" in body:
                    return {"success": True, "buckets": body.get("buckets", [])}
                return {"success": True, "buckets": []}
            if status_code == 403:
                return {"success": False, "error": "权限不足", "error_code": 403}

            body = result.get("body", {})
            if isinstance(body, str):
                try:
                    body = json.loads(body)
                except json.JSONDecodeError:
                    body = {}
            error_msg = f"HTTP {status_code}"
            if isinstance(body, dict) and "error" in body:
                error_msg = (
                    body.get("error", {}).get("message", error_msg)
                    if isinstance(body.get("error"), dict)
                    else str(body.get("error", error_msg))
                )
            return {"success": False, "error": error_msg, "error_code": status_code}

        return {"success": False, "error": "获取配额失败", "error_code": 0}

    async def get_google_quota(
        self, auth_index: str, provider: str = "antigravity", filename: str = ""
    ) -> Dict[str, Any]:
        if provider.lower() in ("gemini", "gemini-cli"):
            project = extract_project_from_filename(filename)
            if not project:
                return {
                    "success": False,
                    "error": "无法从文件名提取项目名称",
                    "error_code": 0,
                }
            return await self.get_gemini_cli_quota(auth_index, project)

        last_error = None
        last_status_code = None
        for quota_url in ANTIGRAVITY_QUOTA_URLS:
            result = await self.api_call(
                auth_index=auth_index,
                method="POST",
                url=quota_url,
                header=ANTIGRAVITY_REQUEST_HEADERS,
                data="{}",
            )
            if result:
                status_code = result.get("status_code", 0)
                if status_code == 200:
                    body = result.get("body", {})
                    if isinstance(body, dict) and "models" in body:
                        return {"success": True, "models": body.get("models", {})}
                elif status_code == 403:
                    return {"success": False, "error": "权限不足", "error_code": 403}
                else:
                    last_status_code = status_code
                    body = result.get("body", {})
                    if isinstance(body, dict):
                        last_error = body.get("error", {}).get(
                            "message", f"HTTP {status_code}"
                        )
                    else:
                        last_error = f"HTTP {status_code}"

        return {
            "success": False,
            "error": last_error or "获取配额失败",
            "error_code": last_status_code or 0,
        }

    async def get_codex_quota(self, auth_index: str) -> Dict[str, Any]:
        result = await self.api_call(
            auth_index=auth_index,
            method="GET",
            url=CODEX_QUOTA_URL,
            header=CODEX_QUOTA_HEADERS,
            data="",
        )

        if result:
            status_code = result.get("status_code", 0)
            if status_code == 200:
                body = result.get("body", {})
                if isinstance(body, str):
                    try:
                        body = json.loads(body)
                    except json.JSONDecodeError:
                        body = {}

                if isinstance(body, dict) and "rate_limit" in body:
                    return {
                        "success": True,
                        "rate_limit": body.get("rate_limit", {}),
                        "plan_type": body.get("plan_type", "unknown"),
                        "code_review_rate_limit": body.get("code_review_rate_limit"),
                        "credits": body.get("credits"),
                    }
                return {"success": False, "error": "响应格式无效", "error_code": 0}
            if status_code == 401:
                return {
                    "success": False,
                    "error": "认证失败，Token 可能已过期",
                    "error_code": 401,
                }
            if status_code == 403:
                return {"success": False, "error": "权限不足", "error_code": 403}

            body = result.get("body", {})
            if isinstance(body, str):
                try:
                    body = json.loads(body)
                except json.JSONDecodeError:
                    body = {}
            error_msg = f"HTTP {status_code}"
            if isinstance(body, dict) and "error" in body:
                error_msg = (
                    body.get("error", {}).get("message", error_msg)
                    if isinstance(body.get("error"), dict)
                    else str(body.get("error", error_msg))
                )
            return {"success": False, "error": error_msg, "error_code": status_code}

        return {"success": False, "error": "获取配额失败", "error_code": 0}
