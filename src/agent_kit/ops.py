"""安装 / 更新 / 校验操作：渲染模板并管理目标项目的静态规则文件。"""

from dataclasses import dataclass
from pathlib import Path

from agent_kit import catalog, project
from agent_kit.errors import AgentKitError, ConfigError
from agent_kit.render import render

TEMPLATE_DIR = Path(__file__).resolve().parent / "template"

_FIXED_FILES = (
    "AGENT.md",
    ".agents/FOR_AGENT.md",
    ".agents/MEMORY/MEMORY_RULE.md",
    ".agents/TEMP_FILES/TEMP_FILE_RULE.md",
)

_RUNTIME_DIRS = (
    ".agents/MEMORY/memorys",
    ".agents/TEMP_FILES/tmps",
)

_GITIGNORE_MARKER = "# Agent runtime data"
_GITIGNORE_SECTION = """# Agent runtime data
.agents/MEMORY/memorys/*
.agents/TEMP_FILES/tmps/*
!.agents/MEMORY/memorys/.gitkeep
!.agents/TEMP_FILES/tmps/.gitkeep
"""


@dataclass(frozen=True)
class Report:
    """一次操作的结果。"""

    files: list[str]
    """本次写入（或 ``--check`` 发现漂移）的受管文件（相对路径）。"""

    notes: list[str]
    """附加提示（如未托管的技能文件）。"""


def install(
    target: Path,
    *,
    summary: str | None = None,
    package: str | None = None,
    enable: list[str] | None = None,
    disable: list[str] | None = None,
    force: bool = False,
) -> Report:
    """把 agent_kit 安装到目标项目：渲染静态规则、写入配置、追加 .gitignore。"""
    target = target.resolve()
    if not target.is_dir():
        raise AgentKitError(f"目标目录不存在：{target}")
    if (target / ".agents").exists() and not force:
        raise AgentKitError(
            "目标项目已存在 .agents/；更新请运行 agent-kit update"
            "（或使用 --force 重新安装）"
        )
    config = project.detect(target, summary=summary, package=package)
    config.skills = _select_skills(enable or [], disable or [])
    files = render_files(config)
    project.save_config(target, config)
    written = _write_files(target, files)
    _ensure_runtime(target)
    _ensure_gitignore(target)
    return Report(files=written, notes=[])


def update(target: Path, *, check: bool = False) -> Report:
    """按配置重新渲染受管文件；``check=True`` 时只报告漂移、不写入。"""
    target = target.resolve()
    config = project.load_config(target)
    files = render_files(config)
    changed = [
        rel
        for rel, content in files.items()
        if not (target / rel).is_file()
        or (target / rel).read_text(encoding="utf-8") != content
    ]
    notes = _local_skill_notes(target, config)
    if check:
        drift = list(changed)
        if not _gitignore_has_section(target):
            drift.append(".gitignore（缺少 Agent runtime data 段）")
        return Report(files=drift, notes=notes)
    _write_files(target, {rel: files[rel] for rel in changed})
    _ensure_runtime(target)
    _ensure_gitignore(target)
    return Report(files=changed, notes=notes)


def render_files(config: project.ProjectConfig) -> dict[str, str]:
    """按配置渲染全部受管文件（相对路径 -> 内容）。"""
    values = _values(config)
    files = {rel: render(_template_text(rel), values) for rel in _FIXED_FILES}
    for name in config.skills:
        rel = f".agents/SKILLS/{name}.md"
        files[rel] = render(_template_text(rel), values)
    return files


def _select_skills(enable: list[str], disable: list[str]) -> list[str]:
    known = catalog.by_name()
    unknown = sorted({*enable, *disable} - set(known))
    if unknown:
        raise ConfigError(f"未知技能：{', '.join(unknown)}")
    enabled = set(enable)
    disabled = set(disable)
    return [
        skill.name
        for skill in catalog.CATALOG
        if (skill.enabled_by_default or skill.name in enabled)
        and skill.name not in disabled
    ]


def _values(config: project.ProjectConfig) -> dict[str, str]:
    if "publish" in config.skills and (not config.repo_url or not config.pypi_name):
        raise ConfigError(
            "启用 publish 技能需要在 [project] 配置 repo_url 与 pypi_name"
        )
    skills = [catalog.by_name()[name] for name in config.skills]
    toolchain = config.toolchain
    return {
        "PROJECT_NAME": config.name,
        "PROJECT_SUMMARY": config.summary,
        "PACKAGE": config.package,
        "SRC_DIR": config.src_dir,
        "PACKAGE_INIT": config.package_init,
        "SETUP_CMD": toolchain.setup,
        "LINT_CMD": toolchain.lint,
        "FORMAT_CMD": toolchain.format,
        "TYPECHECK_CMD": toolchain.typecheck,
        "TEST_CMD": toolchain.test,
        "SKILLS_TREE": _skills_tree(skills),
        "SKILLS_SUMMARY": "、".join(skill.title for skill in skills),
        "SKILLS_TABLE": _skills_table(skills),
        "GATE_STEPS": _gate_steps(config),
        "EXTRA_SOURCES": "\n".join(
            _source_row(entry) for entry in config.extra_sources
        ),
        "REPO_URL": config.repo_url,
        "PYPI_NAME": config.pypi_name,
    }


def _skills_tree(skills: list[catalog.Skill]) -> str:
    names = [f"{skill.name}.md" for skill in skills]
    width = max(26, max(len(name) for name in names))
    lines: list[str] = []
    for index, (name, skill) in enumerate(zip(names, skills, strict=True)):
        branch = "└──" if index == len(names) - 1 else "├──"
        lines.append(f"│   {branch} {name.ljust(width)}#   {skill.title}")
    return "\n".join(lines)


def _skills_table(skills: list[catalog.Skill]) -> str:
    lines = [
        "| 任务 | SKILL 文件 |",
        "| --- | --- |",
    ]
    lines.extend(
        f"| {skill.title} | [{skill.name}.md](SKILLS/{skill.name}.md) |"
        for skill in skills
    )
    return "\n".join(lines)


def _gate_steps(config: project.ProjectConfig) -> str:
    toolchain = config.toolchain
    src = config.src_dir
    windows_glob = src.replace("/", "\\") + r"\**\*.py"
    steps = [
        f"`{toolchain.lint}` — lint 检查",
        f"`{toolchain.format}` — 格式化（仅检查不写入时，为命令追加 `--check`）",
        f"**零遮蔽检查** — `{src}/` 下不得出现任何 `# type:` 或 `# pyright` 注释\n"
        f"   - Windows: `Select-String -Path {windows_glob} "
        f'-Pattern "# type:|# pyright"` 应无匹配\n'
        f'   - Unix: `grep -r "# type:\\|# pyright" {src}/` 应无输出',
        f"`{toolchain.typecheck}` — 类型检查（必须零错误）",
        f"`{toolchain.test}` — 全量测试",
    ]
    for extra in toolchain.extras:
        command, _, description = extra.partition(" :: ")
        steps.append(f"`{command.strip()}` — {description.strip() or '附加验证'}")
    return "\n".join(f"{number}. {step}" for number, step in enumerate(steps, 1))


def _source_row(entry: str) -> str:
    path, _, description = entry.partition(" :: ")
    text = description.strip()
    return f"| `{path.strip()}` | {text} |"


def _template_text(rel: str) -> str:
    path = TEMPLATE_DIR / rel
    if not path.is_file():
        raise AgentKitError(f"模板缺失：{rel}")
    return path.read_text(encoding="utf-8")


def _write_files(target: Path, files: dict[str, str]) -> list[str]:
    written: list[str] = []
    for rel, content in files.items():
        path = target / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        written.append(rel)
    return written


def _ensure_runtime(target: Path) -> None:
    for rel in _RUNTIME_DIRS:
        directory = target / rel
        directory.mkdir(parents=True, exist_ok=True)
        (directory / ".gitkeep").touch()


def _ensure_gitignore(target: Path) -> None:
    path = target / ".gitignore"
    existing = path.read_text(encoding="utf-8") if path.is_file() else ""
    if _GITIGNORE_MARKER in existing:
        return
    prefix = existing
    if prefix and not prefix.endswith("\n"):
        prefix += "\n"
    if prefix and not prefix.endswith("\n\n"):
        prefix += "\n"
    path.write_text(prefix + _GITIGNORE_SECTION, encoding="utf-8")


def _gitignore_has_section(target: Path) -> bool:
    path = target / ".gitignore"
    return path.is_file() and _GITIGNORE_MARKER in path.read_text(encoding="utf-8")


def _local_skill_notes(target: Path, config: project.ProjectConfig) -> list[str]:
    directory = target / ".agents" / "SKILLS"
    if not directory.is_dir():
        return []
    managed = {f"{name}.md" for name in config.skills}
    extras = sorted(
        entry.name
        for entry in directory.iterdir()
        if entry.is_file() and entry.suffix == ".md" and entry.name not in managed
    )
    if not extras:
        return []
    return [f"未托管技能文件（update 不会修改）：{', '.join(extras)}"]
