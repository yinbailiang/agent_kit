"""安装 / 更新操作测试。"""

from pathlib import Path

import pytest

from agent_kit import ops
from agent_kit.errors import AgentKitError, ConfigError


def test_install_creates_expected_files(demo_project: Path) -> None:
    report = ops.install(demo_project)
    assert "AGENT.md" in report.files
    agents = demo_project / ".agents"
    assert (agents / "FOR_AGENT.md").is_file()
    assert (agents / "agent_kit.toml").is_file()
    assert (agents / "MEMORY" / "memorys" / ".gitkeep").is_file()
    assert (agents / "TEMP_FILES" / "tmps" / ".gitkeep").is_file()
    # 默认技能：除 publish 外全部启用
    assert (agents / "SKILLS" / "pre-commit-check.md").is_file()
    assert not (agents / "SKILLS" / "publish.md").exists()
    # 占位符已全部渲染
    agent_md = (demo_project / "AGENT.md").read_text(encoding="utf-8")
    assert "demo" in agent_md
    assert "{{" not in agent_md
    gate = (agents / "SKILLS" / "pre-commit-check.md").read_text(encoding="utf-8")
    assert "uv run pytest -q" in gate


def test_install_requires_pyproject(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match=r"pyproject\.toml"):
        ops.install(tmp_path)


def test_install_twice_is_rejected(demo_project: Path) -> None:
    ops.install(demo_project)
    with pytest.raises(AgentKitError, match="agent-kit update"):
        ops.install(demo_project)


def test_install_force_reinstalls(demo_project: Path) -> None:
    ops.install(demo_project)
    report = ops.install(demo_project, force=True)
    assert "AGENT.md" in report.files


def test_install_unknown_skill_rejected(demo_project: Path) -> None:
    with pytest.raises(ConfigError, match="未知技能"):
        ops.install(demo_project, enable=["nope"])


def test_install_skill_selection(demo_project: Path) -> None:
    ops.install(demo_project, disable=["write-docs", "modify-core-api"])
    skills_dir = demo_project / ".agents" / "SKILLS"
    assert not (skills_dir / "write-docs.md").exists()
    assert (skills_dir / "write-tests.md").is_file()
    agent_md = (demo_project / "AGENT.md").read_text(encoding="utf-8")
    assert "write-docs.md" not in agent_md
    assert "write-tests.md" in agent_md


def test_publish_requires_repo_metadata(demo_project: Path) -> None:
    with pytest.raises(ConfigError, match="repo_url"):
        ops.install(demo_project, enable=["publish"])


def test_update_is_idempotent(demo_project: Path) -> None:
    ops.install(demo_project)
    assert ops.update(demo_project).files == []


def test_update_preserves_runtime_data(demo_project: Path) -> None:
    ops.install(demo_project)
    memory = demo_project / ".agents" / "MEMORY" / "memorys" / "session.md"
    memory.write_text("- 保留我", encoding="utf-8")
    tmp_file = demo_project / ".agents" / "TEMP_FILES" / "tmps" / "debug.txt"
    tmp_file.write_text("tmp", encoding="utf-8")
    ops.update(demo_project)
    assert memory.read_text(encoding="utf-8") == "- 保留我"
    assert tmp_file.is_file()


def test_update_check_detects_drift(demo_project: Path) -> None:
    ops.install(demo_project)
    assert ops.update(demo_project, check=True).files == []
    (demo_project / "AGENT.md").write_text("手工改动", encoding="utf-8")
    drift = ops.update(demo_project, check=True)
    assert "AGENT.md" in drift.files
    # check 模式不写入
    assert (demo_project / "AGENT.md").read_text(encoding="utf-8") == "手工改动"


def test_update_repairs_missing_file(demo_project: Path) -> None:
    ops.install(demo_project)
    (demo_project / "AGENT.md").unlink()
    assert "AGENT.md" in ops.update(demo_project).files


def test_update_reports_unmanaged_skills(demo_project: Path) -> None:
    ops.install(demo_project)
    local = demo_project / ".agents" / "SKILLS" / "local-skill.md"
    local.write_text("local", encoding="utf-8")
    report = ops.update(demo_project, check=True)
    assert any("local-skill.md" in note for note in report.notes)
    assert local.is_file()


def test_gitignore_section_is_added_once(demo_project: Path) -> None:
    (demo_project / ".gitignore").write_text(".venv/\n", encoding="utf-8")
    ops.install(demo_project)
    ops.update(demo_project)
    text = (demo_project / ".gitignore").read_text(encoding="utf-8")
    assert text.count("# Agent runtime data") == 1
    assert ".venv/" in text
    assert ".agents/MEMORY/memorys/*" in text
