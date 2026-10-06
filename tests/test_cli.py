"""命令行入口测试。"""

from pathlib import Path

import pytest

from agent_kit.cli import main


def test_list_shows_catalog(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["list"]) == 0
    out = capsys.readouterr().out
    assert "pre-commit-check" in out
    assert "publish" in out


def test_install_then_check(
    demo_project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["install", "--target", str(demo_project)]) == 0
    assert (demo_project / "AGENT.md").is_file()
    capsys.readouterr()
    assert main(["update", "--target", str(demo_project), "--check"]) == 0


def test_check_reports_drift_with_exit_code(
    demo_project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    main(["install", "--target", str(demo_project)])
    (demo_project / "AGENT.md").write_text("手工改动", encoding="utf-8")
    assert main(["update", "--target", str(demo_project), "--check"]) == 1
    assert "AGENT.md" in capsys.readouterr().out


def test_error_returns_nonzero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["install", "--target", str(tmp_path)]) == 1
    assert "错误" in capsys.readouterr().err
