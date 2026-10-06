"""共享 fixture：最小 uv 项目。"""

from pathlib import Path

import pytest


@pytest.fixture
def demo_project(tmp_path: Path) -> Path:
    """最小 uv 项目（src 布局 + uv_build module-name）。"""
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "demo"\ndescription = "示例项目"\n'
        '\n[tool.uv.build-backend]\nmodule-root = "src"\nmodule-name = "demo"\n',
        encoding="utf-8",
    )
    return tmp_path
