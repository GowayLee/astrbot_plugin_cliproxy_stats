# Package Relative Imports Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix AstrBot package loading so the plugin imports its internal modules reliably during installation and startup.

**Architecture:** Keep the existing flat plugin layout and convert internal imports to package-relative imports. Mark the plugin root as a Python package with `__init__.py`, then add a regression test that imports the plugin through a package path matching AstrBot's loader behavior.

**Tech Stack:** Python, unittest, AstrBot plugin package layout

---

### Task 1: Add a failing package-import regression test

**Files:**
- Create: `tests/test_package_imports.py`

- [ ] **Step 1: Write the failing test**

```python
import importlib
import sys
import tempfile
from pathlib import Path
from unittest import TestCase


class PackageImportTest(TestCase):
    def test_import_main_via_package_path(self):
        ...
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_package_imports -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'builders'`

### Task 2: Convert internal imports to package-relative imports

**Files:**
- Create: `__init__.py`
- Modify: `main.py`
- Modify: `builders.py`
- Modify: `client.py`
- Modify: `llm_analysis.py`

- [ ] **Step 1: Write minimal implementation**

```python
from .builders import ...
from .constants import ...
```

- [ ] **Step 2: Run test to verify it passes**

Run: `python -m unittest tests.test_package_imports -v`
Expected: PASS

### Task 3: Verify compilation still works

**Files:**
- Modify: none

- [ ] **Step 1: Run syntax validation**

Run: `python -m py_compile main.py constants.py client.py quota_parser.py builders.py text_renderer.py llm_analysis.py`
Expected: command exits successfully

- [ ] **Step 2: Run package import check**

Run: `python -m unittest tests.test_package_imports -v`
Expected: PASS
