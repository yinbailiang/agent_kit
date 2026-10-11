"""技能目录：agent_kit 随包分发的标准技能清单（单一源头）。"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Skill:
    """一个标准技能。

    ``name`` 是模板文件的 stem（对应 ``.agents/SKILLS/<name>.md``）；
    ``title`` 是技能中文名，用于生成 AGENT.md 的目录树与技能表；
    ``enabled_by_default`` 决定 ``install`` 时的默认启用状态。
    """

    name: str
    title: str
    enabled_by_default: bool = True


CATALOG: tuple[Skill, ...] = (
    Skill("modify-core-api", "修改核心 API"),
    Skill("pre-commit-check", "审查前检查"),
    Skill("write-tests", "编写测试"),
    Skill("write-docs", "编写文档"),
    Skill("write-skill", "创建通用技能"),
    Skill("init-project", "初始化新项目"),
    Skill("setup-cicd", "配置 GitHub CI/CD"),
    Skill("publish", "项目发布", enabled_by_default=False),
)


def by_name() -> dict[str, Skill]:
    """返回 ``name -> Skill`` 映射。"""
    return {skill.name: skill for skill in CATALOG}
