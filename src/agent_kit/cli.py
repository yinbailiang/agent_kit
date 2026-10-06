"""agent-kit 命令行入口。"""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from agent_kit import catalog, ops
from agent_kit.errors import AgentKitError


def main(argv: Sequence[str] | None = None) -> int:
    """命令行入口；返回进程退出码。"""
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        match args.command:
            case "list":
                _print_catalog()
                return 0
            case "install":
                report = ops.install(
                    Path(args.target),
                    summary=args.summary,
                    package=args.package,
                    enable=args.enable,
                    disable=args.disable,
                    force=args.force,
                )
                _print_report("安装完成", report)
                return 0
            case "update":
                report = ops.update(Path(args.target), check=args.check)
                if args.check:
                    if report.files:
                        print("发现漂移（运行 agent-kit update 可修复）：")
                        for rel in report.files:
                            print(f"  - {rel}")
                    else:
                        print("无漂移：所有受管文件与模板一致")
                else:
                    _print_report("更新完成", report)
                _print_notes(report)
                return 1 if args.check and report.files else 0
            case _:
                pass
    except AgentKitError as error:
        print(f"错误：{error}", file=sys.stderr)
        return 1
    raise AssertionError(f"未知命令：{args.command}")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agent-kit",
        description="智能体工程学模板同步工具：把 AGENT.md + .agents 体系"
        "安装 / 更新到目标项目。",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("list", help="列出技能目录")

    install = subparsers.add_parser("install", help="安装到目标项目")
    install.add_argument("--target", default=".", help="目标项目路径（默认当前目录）")
    install.add_argument(
        "--summary", default=None, help="项目概述（默认取 pyproject description）"
    )
    install.add_argument("--package", default=None, help="包名（默认自动探测）")
    install.add_argument(
        "--enable", action="append", default=[], help="额外启用技能（可重复）"
    )
    install.add_argument(
        "--disable", action="append", default=[], help="禁用技能（可重复）"
    )
    install.add_argument("--force", action="store_true", help="覆盖已存在的 .agents/")

    update = subparsers.add_parser("update", help="按配置更新受管文件")
    update.add_argument("--target", default=".", help="目标项目路径（默认当前目录）")
    update.add_argument(
        "--check", action="store_true", help="只检查漂移不写入；有漂移时退出码为 1"
    )
    return parser


def _print_catalog() -> None:
    print("可用技能：")
    for skill in catalog.CATALOG:
        default = "默认启用" if skill.enabled_by_default else "按需启用"
        print(f"  {skill.name:<20} {skill.title}（{default}）")


def _print_report(title: str, report: ops.Report) -> None:
    print(title)
    if not report.files:
        print("  无文件变化")
    for rel in report.files:
        print(f"  + {rel}")
    _print_notes(report)


def _print_notes(report: ops.Report) -> None:
    for note in report.notes:
        print(f"  注意：{note}")
