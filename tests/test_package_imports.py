import importlib
import shutil
import sys
import tempfile
from pathlib import Path
from unittest import TestCase


class PackageImportTest(TestCase):
    def test_import_main_via_package_path(self):
        repo_root = Path(__file__).resolve().parent.parent

        with tempfile.TemporaryDirectory() as tmpdir:
            temp_root = Path(tmpdir)
            plugin_name = repo_root.name
            package_root = temp_root / "data" / "plugins"
            plugin_link = package_root / plugin_name
            package_root.mkdir(parents=True)

            try:
                plugin_link.symlink_to(repo_root, target_is_directory=True)
            except OSError:
                shutil.copytree(repo_root, plugin_link)

            self._write_astrbot_stubs(temp_root)
            self._write_package_markers(temp_root, plugin_name)

            original_sys_path = sys.path[:]
            sys.path[:] = [
                entry for entry in sys.path if Path(entry or ".").resolve() != repo_root
            ]
            sys.path.insert(0, str(temp_root))
            try:
                module = importlib.import_module(f"data.plugins.{plugin_name}.main")
            finally:
                sys.path[:] = original_sys_path
                self._purge_modules(plugin_name)

        self.assertTrue(hasattr(module, "Main"))

    def _write_package_markers(self, temp_root: Path, plugin_name: str) -> None:
        for path in [
            temp_root / "data",
            temp_root / "data" / "plugins",
            temp_root / "data" / "plugins" / plugin_name,
        ]:
            path.mkdir(parents=True, exist_ok=True)
            init_file = path / "__init__.py"
            init_file.touch(exist_ok=True)

    def _write_astrbot_stubs(self, temp_root: Path) -> None:
        files = {
            temp_root / "astrbot" / "__init__.py": "",
            temp_root / "astrbot" / "api" / "__init__.py": (
                "class AstrBotConfig(dict):\n"
                "    def get(self, key, default=None):\n"
                "        return super().get(key, default)\n\n"
                "class _Logger:\n"
                "    def info(self, *args, **kwargs):\n"
                "        pass\n\n"
                "    def warning(self, *args, **kwargs):\n"
                "        pass\n\n"
                "    def error(self, *args, **kwargs):\n"
                "        pass\n\n"
                "    def debug(self, *args, **kwargs):\n"
                "        pass\n\n"
                "logger = _Logger()\n"
            ),
            temp_root / "astrbot" / "api" / "event" / "__init__.py": (
                "class AstrMessageEvent:\n"
                "    def __init__(self):\n"
                "        self.message_str = ''\n\n"
                "    def plain_result(self, text):\n"
                "        return text\n\n"
                "class _Filter:\n"
                "    def command(self, _name):\n"
                "        def decorator(func):\n"
                "            return func\n"
                "        return decorator\n\n"
                "filter = _Filter()\n"
            ),
            temp_root / "astrbot" / "api" / "star" / "__init__.py": (
                "class Context:\n"
                "    pass\n\n"
                "class Star:\n"
                "    def __init__(self, context):\n"
                "        self.context = context\n"
            ),
            temp_root / "astrbot" / "core" / "__init__.py": "",
            temp_root / "astrbot" / "core" / "provider" / "__init__.py": "",
            temp_root / "astrbot" / "core" / "provider" / "provider.py": (
                "class Provider:\n    pass\n"
            ),
            temp_root / "aiohttp" / "__init__.py": (
                "class ClientTimeout:\n"
                "    def __init__(self, *args, **kwargs):\n"
                "        pass\n\n"
                "class TCPConnector:\n"
                "    def __init__(self, *args, **kwargs):\n"
                "        pass\n\n"
                "class ClientSession:\n"
                "    def __init__(self, *args, **kwargs):\n"
                "        self.closed = False\n\n"
                "    async def close(self):\n"
                "        self.closed = True\n"
            ),
        }

        for path, content in files.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")

    def _purge_modules(self, plugin_name: str) -> None:
        prefixes = [
            f"data.plugins.{plugin_name}",
            "data.plugins",
            "data",
            "astrbot",
        ]
        for module_name in list(sys.modules):
            if any(
                module_name == prefix or module_name.startswith(prefix + ".")
                for prefix in prefixes
            ):
                sys.modules.pop(module_name, None)
