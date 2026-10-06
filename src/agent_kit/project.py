"""目标项目探测与 agent_kit 配置（.agents/agent_kit.toml）的读写。"""

import json
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

from agent_kit import catalog
from agent_kit.errors import ConfigError

KIT_VERSION = 1
CONFIG_RELPATH = ".agents/agent_kit.toml"


@dataclass
class Toolchain:
    """项目工具链命令（安装时的默认值，可在配置中按项目覆盖）。"""

    setup: str = "uv sync --extra dev"
    lint: str = "uv run ruff check ."
    format: str = "uv run ruff format ."
    typecheck: str = "uv run pyright"
    test: str = "uv run pytest -q"
    extras: list[str] = field(default_factory=list[str])


@dataclass
class ProjectConfig:
    """agent_kit 在目标项目中的配置。"""

    name: str
    summary: str
    package: str
    src_dir: str
    repo_url: str = ""
    pypi_name: str = ""
    extra_sources: list[str] = field(default_factory=list[str])
    toolchain: Toolchain = field(default_factory=Toolchain)
    skills: list[str] = field(
        default_factory=lambda: [
            skill.name for skill in catalog.CATALOG if skill.enabled_by_default
        ]
    )

    @property
    def package_init(self) -> str:
        """包入口文件路径（如 ``src/scanf/__init__.py``）。"""
        return f"{self.src_dir}/__init__.py"


def config_path(target: Path) -> Path:
    """目标项目中 agent_kit 配置文件的路径。"""
    return target / CONFIG_RELPATH


def detect(
    target: Path, *, summary: str | None = None, package: str | None = None
) -> ProjectConfig:
    """从目标项目探测基础信息（名称 / 概述 / 包名），构建默认配置。"""
    pyproject = target / "pyproject.toml"
    if not pyproject.is_file():
        raise ConfigError(f"目标目录缺少 pyproject.toml：{target}")
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    raw = data.get("project")
    section = cast(dict[str, Any], raw) if isinstance(raw, dict) else {}
    name = section.get("name")
    if not isinstance(name, str) or not name:
        raise ConfigError("pyproject.toml 缺少 [project] name")
    resolved_summary = summary if summary is not None else _description(section)
    if not resolved_summary:
        raise ConfigError(
            "缺少项目概述：请通过 --summary 或 pyproject.toml 的 description 提供"
        )
    resolved_package = package or _detect_package(target, data)
    return ProjectConfig(
        name=name,
        summary=resolved_summary,
        package=resolved_package,
        src_dir=f"src/{resolved_package}",
    )


def _description(section: dict[str, Any]) -> str:
    value = section.get("description")
    return value if isinstance(value, str) else ""


def _detect_package(target: Path, data: dict[str, Any]) -> str:
    tool = data.get("tool")
    if isinstance(tool, dict):
        uv = cast(dict[str, Any], tool).get("uv")
        if isinstance(uv, dict):
            backend = cast(dict[str, Any], uv).get("build-backend")
            if isinstance(backend, dict):
                module = cast(dict[str, Any], backend).get("module-name")
                if isinstance(module, str) and module:
                    return module
    src = target / "src"
    candidates = (
        sorted(
            entry.name
            for entry in src.iterdir()
            if entry.is_dir() and (entry / "__init__.py").is_file()
        )
        if src.is_dir()
        else []
    )
    if len(candidates) == 1:
        return candidates[0]
    raise ConfigError(
        "无法确定包名：请在 pyproject.toml 配置 [tool.uv.build-backend] module-name，"
        "或使用 --package 指定"
    )


def save_config(target: Path, config: ProjectConfig) -> Path:
    """把配置写入目标项目（覆盖已有文件）。"""
    path = config_path(target)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dumps(config), encoding="utf-8")
    return path


def load_config(target: Path) -> ProjectConfig:
    """读取目标项目的配置；未安装时报错。"""
    path = config_path(target)
    if not path.is_file():
        raise ConfigError(
            "目标项目未安装 agent-kit（缺少 .agents/agent_kit.toml）；"
            "请先运行 agent-kit install"
        )
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    project = _table(data, "project")
    toolchain = _table(data, "toolchain")
    skills = _str_list(_table(data, "skills"), "enabled", "skills")
    unknown = [name for name in skills if name not in catalog.by_name()]
    if unknown:
        raise ConfigError(f"配置引用了未知技能：{', '.join(unknown)}")
    return ProjectConfig(
        name=_str_field(project, "name", "project"),
        summary=_str_field(project, "summary", "project"),
        package=_str_field(project, "package", "project"),
        src_dir=_str_field(project, "src_dir", "project"),
        repo_url=_opt_str_field(project, "repo_url"),
        pypi_name=_opt_str_field(project, "pypi_name"),
        extra_sources=_opt_str_list(project, "extra_sources"),
        toolchain=Toolchain(
            setup=_str_field(toolchain, "setup", "toolchain"),
            lint=_str_field(toolchain, "lint", "toolchain"),
            format=_str_field(toolchain, "format", "toolchain"),
            typecheck=_str_field(toolchain, "typecheck", "toolchain"),
            test=_str_field(toolchain, "test", "toolchain"),
            extras=_opt_str_list(toolchain, "extras"),
        ),
        skills=skills,
    )


def dumps(config: ProjectConfig) -> str:
    """把配置序列化为 TOML 文本（受控 schema 的最小实现）。"""
    return "\n".join(
        [
            "# agent_kit 项目配置（由 agent-kit 生成；"
            "可手工微调，改动在下次 update 时生效）",
            f"kit_version = {KIT_VERSION}",
            "",
            "[project]",
            f"name = {_string(config.name)}",
            f"summary = {_string(config.summary)}",
            f"package = {_string(config.package)}",
            f"src_dir = {_string(config.src_dir)}",
            f"repo_url = {_string(config.repo_url)}",
            f"pypi_name = {_string(config.pypi_name)}",
            f"extra_sources = {_strings(config.extra_sources)}",
            "",
            "[toolchain]",
            f"setup = {_string(config.toolchain.setup)}",
            f"lint = {_string(config.toolchain.lint)}",
            f"format = {_string(config.toolchain.format)}",
            f"typecheck = {_string(config.toolchain.typecheck)}",
            f"test = {_string(config.toolchain.test)}",
            f"extras = {_strings(config.toolchain.extras)}",
            "",
            "[skills]",
            f"enabled = {_strings(config.skills)}",
            "",
        ]
    )


def _table(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        raise ConfigError(f"配置缺少 [{key}] 段")
    return cast(dict[str, Any], value)


def _str_field(section: dict[str, Any], key: str, where: str) -> str:
    value = section.get(key)
    if not isinstance(value, str) or not value:
        raise ConfigError(f"配置字段缺失或无效：{where}.{key}")
    return value


def _opt_str_field(section: dict[str, Any], key: str) -> str:
    value = section.get(key, "")
    return value if isinstance(value, str) else ""


def _str_list(section: dict[str, Any], key: str, where: str) -> list[str]:
    value = section.get(key)
    if not isinstance(value, list):
        raise ConfigError(f"配置字段缺失或无效：{where}.{key}")
    items = cast(list[Any], value)
    result = [item for item in items if isinstance(item, str)]
    if len(result) != len(items):
        raise ConfigError(f"配置字段缺少或无效：{where}.{key}")
    return result


def _opt_str_list(section: dict[str, Any], key: str) -> list[str]:
    value = section.get(key, [])
    if not isinstance(value, list):
        return []
    return [item for item in cast(list[Any], value) if isinstance(item, str)]


def _string(value: str) -> str:
    # json 字符串转义（\" \\ \n \uXXXX 等）与 TOML basic string 兼容
    return json.dumps(value, ensure_ascii=False)


def _strings(values: list[str]) -> str:
    return "[" + ", ".join(_string(value) for value in values) + "]"
