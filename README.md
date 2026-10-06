# agent_kit — 智能体工程学模板与同步工具

> **单一源头**：把 event_bus 项目中沉淀的「智能体工程学」设计（`AGENT.md` + `.agents/` 体系）
> 抽成可参数化模板，一条命令安装 / 更新到任意项目。

## 背景

多项目各自维护一份 `.agents/` 会逐渐漂移（如 psyche 的副本已落后于 event_bus）。
本仓是这套设计的**唯一源头**：模板在此演进，通过 `agent-kit` 分发到各项目。

## 体系构成

安装到目标项目后产生：

```text
项目根/
├── AGENT.md                      # 引导入口（目录树 + 工作流）
└── .agents/
    ├── agent_kit.toml            # 项目配置（名称 / 工具链 / 启用技能）
    ├── FOR_AGENT.md              # 行为准则与编码规范
    ├── SKILLS/                   # 任务技能
    │   ├── modify-core-api.md
    │   ├── pre-commit-check.md
    │   ├── write-tests.md
    │   ├── write-docs.md
    │   └── write-skill.md
    ├── MEMORY/                   # 跨会话记忆（memorys/ 不入库）
    └── TEMP_FILES/               # 会话临时文件（tmps/ 不入库）
```

## 快速开始

```bash
cd /home/yinbailiang/Desktop/InfinitySystem/neo/agent_kit
uv sync                    # 首次：准备工具环境

# 安装到目标项目
uv run agent-kit install --target /path/to/project

# 更新（模板演进后同步到项目；memorys/ 与 tmps/ 永不触碰）
uv run agent-kit update --target /path/to/project
uv run agent-kit update --target /path/to/project --check   # 仅检查漂移（退出码 1 = 有漂移）

# 查看技能目录
uv run agent-kit list
```

## 配置

安装时自动探测（`pyproject.toml` 的 name / description / module-name、src 布局包名），
结果写入目标项目 `.agents/agent_kit.toml`，可手工微调后运行 `update` 生效：

| 字段 | 说明 |
| --- | --- |
| `project.name` | 项目名（模板 `{{PROJECT_NAME}}`） |
| `project.summary` | 一句话概述（`--summary` 可覆盖） |
| `project.package` / `src_dir` | 包名与源码目录（`--package` 可覆盖） |
| `project.repo_url` / `pypi_name` | 发布技能所需（启用 publish 时必填） |
| `project.extra_sources` | 追加到「信息源」表的行，如 `"example.py :: 可运行示例"` |
| `toolchain.*` | setup / lint / format / typecheck / test 命令（渲染进技能步骤） |
| `toolchain.extras` | 提交前检查的附加步骤，如 `"uv run python example.py :: 示例冒烟"` |
| `skills.enabled` | 启用的技能列表（默认：除 publish 外全部） |

> 启用 `publish` 技能：先安装，再编辑配置补上 `repo_url` / `pypi_name` 并把 `"publish"`
> 加入 `skills.enabled`，最后运行 `agent-kit update`。

## 模板占位符

模板存于 `src/agent_kit/template/`，支持以下占位符（`{{TOKEN}}` 之外的文字原样保留）：

| 占位符 | 来源 |
| --- | --- |
| `{{PROJECT_NAME}}` `{{PROJECT_SUMMARY}}` `{{PACKAGE}}` `{{SRC_DIR}}` `{{PACKAGE_INIT}}` | `[project]` 配置 |
| `{{SETUP_CMD}}` `{{LINT_CMD}}` `{{FORMAT_CMD}}` `{{TYPECHECK_CMD}}` `{{TEST_CMD}}` | `[toolchain]` 配置 |
| `{{SKILLS_TREE}}` `{{SKILLS_SUMMARY}}` `{{SKILLS_TABLE}}` | 由启用技能生成 |
| `{{GATE_STEPS}}` | 由工具链命令生成（pre-commit-check 步骤） |
| `{{EXTRA_SOURCES}}` | 由 `extra_sources` 生成 |
| `{{REPO_URL}}` `{{PYPI_NAME}}` | `[project]` 配置（publish 技能） |

## 设计原则

- **单一源头**：静态规则只能通过模板演化 + `update` 分发；项目内直接修改会被覆盖
- **运行时数据永不被 update 触碰**：`memorys/` 与 `tmps/` 只在安装时创建
- **前端无关**：不引入 YAML 头、特定工具名等任一端专属格式（见 `write-skill` 技能）
- **可校验**：`update --check` 可接入各项目 CI，发现规则漂移

## 接入状态

| 项目 | 状态 |
| --- | --- |
| event_bus | 原版（本仓模板的设计来源；后续可按本仓配置反向接入） |
| pyscanf | 已接入 |
| psyche | 旧版副本，待迁移 |
| 其他 neo 项目 | 待接入 |

## 开发

```bash
uv sync --extra dev
uv run ruff format . && uv run ruff check .
uv run pytest -q
uv run pyright
```
