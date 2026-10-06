"""配置探测与读写测试。"""

from pathlib import Path

import pytest

from agent_kit import project
from agent_kit.errors import ConfigError


def _write_pyproject(root: Path, *, with_module_name: bool = True) -> None:
    section = (
        '\n[tool.uv.build-backend]\nmodule-root = "src"\nmodule-name = "demo"\n'
        if with_module_name
        else ""
    )
    (root / "pyproject.toml").write_text(
        f'[project]\nname = "demo"\ndescription = "示例项目"\n{section}',
        encoding="utf-8",
    )


def test_detect_reads_pyproject(tmp_path: Path) -> None:
    _write_pyproject(tmp_path)
    config = project.detect(tmp_path)
    assert config.name == "demo"
    assert config.summary == "示例项目"
    assert config.package == "demo"
    assert config.src_dir == "src/demo"
    assert config.package_init == "src/demo/__init__.py"
    assert config.skills == [
        "modify-core-api",
        "pre-commit-check",
        "write-tests",
        "write-docs",
        "write-skill",
    ]


def test_detect_summary_override(tmp_path: Path) -> None:
    _write_pyproject(tmp_path)
    assert project.detect(tmp_path, summary="覆盖概述").summary == "覆盖概述"


def test_detect_falls_back_to_src_scan(tmp_path: Path) -> None:
    _write_pyproject(tmp_path, with_module_name=False)
    package_dir = tmp_path / "src" / "demo"
    package_dir.mkdir(parents=True)
    (package_dir / "__init__.py").write_text("", encoding="utf-8")
    assert project.detect(tmp_path).package == "demo"


def test_detect_requires_pyproject(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match=r"pyproject\.toml"):
        project.detect(tmp_path)


def test_config_roundtrip(tmp_path: Path) -> None:
    config = project.ProjectConfig(
        name="demo",
        summary="概述",
        package="demo",
        src_dir="src/demo",
        repo_url="https://example.com/demo",
        pypi_name="demo",
        extra_sources=["example.py :: 可运行示例"],
    )
    config.toolchain.extras.append("uv run python example.py :: 示例冒烟")
    project.save_config(tmp_path, config)
    assert project.load_config(tmp_path) == config


def test_load_config_requires_install(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="未安装"):
        project.load_config(tmp_path)
