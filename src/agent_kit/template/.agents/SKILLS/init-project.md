# SKILL: 初始化新项目

**触发**：新项目、初始化项目、创建项目、项目模板、脚手架、bootstrap、从零建项。

## 目标

按家族规范从零建立一个新项目：uv 工程 → src 布局 → 工具链 → 质量门 →
agent-kit 静态规则 → GitHub CI/CD。

## 目录结构（目标态）

```text
<项目名>/
├── pyproject.toml            # 元数据 / 依赖 / 工具配置
├── README.md                 # 对外说明
├── src/<package>/            # 源码（src 布局）
│   └── __init__.py
├── tests/                    # 测试（镜像源码路径）
│   └── conftest.py
├── .pre-commit-config.yaml   # 本地质量门
├── .github/workflows/        # CI/CD（见 setup-cicd 技能）
├── AGENT.md                  # 引导入口（agent-kit 生成）
└── .agents/                  # 静态规则（agent-kit 生成）
```

## 步骤

1. **创建工程骨架** — 建目录并写入 `pyproject.toml`（尖括号处按项目实际填写）：

   ```toml
   [project]
   name = "<项目名>"
   version = "0.1.0"
   description = "<一句话概述>"
   readme = "README.md"
   requires-python = ">=3.12"
   dependencies = []

   [project.optional-dependencies]
   test = [
       "pytest",
       "pytest-cov",
   ]
   dev = [
       "<项目名>[test]",
       "interrogate",
       "pre-commit",
       "pyright",
       "ruff",
   ]

   [build-system]
   requires = ["uv_build>=0.11.21,<0.12.0"]
   build-backend = "uv_build"

   [tool.uv.build-backend]
   module-root = "src"
   module-name = "<package>"
   ```

2. **创建包与测试骨架** — `src/<package>/__init__.py`（含 docstring 与
   `__version__`）、`tests/conftest.py`（共享 fixture）、至少一个真实测试。

3. **配置工具链**（家族标准）：

   ```toml
   [tool.ruff]
   target-version = "py312"
   line-length = 88
   src = ["src"]

   [tool.ruff.lint]
   select = [
       "B",   # flake8-bugbear
       "C4",  # flake8-comprehensions
       "E",   # pycodestyle (errors)
       "F",   # pyflakes
       "I",   # isort
       "RUF", # Ruff-specific rules
       "SIM", # flake8-simplify
       "UP",  # pyupgrade
       "W",   # pycodestyle (warnings)
   ]

   [tool.ruff.lint.isort]
   known-first-party = ["<package>"]

   [tool.pytest.ini_options]
   testpaths = ["tests"]

   [tool.pyright]
   typeCheckingMode = "strict"
   pythonVersion = "3.12"
   venvPath = "."
   venv = ".venv"

   [tool.interrogate]
   fail-under = 90
   ignore-init-method = true
   ignore-init-module = true
   ignore-magic = true
   ignore-private = true
   ignore-semiprivate = true
   ignore-nested-functions = true
   exclude = ["tests"]
   ```

   > 源码 docstring 使用中文时，在 `[tool.ruff.lint]` 增加
   > `allowed-confusables` 白名单（中文标点），避免 RUF 混淆字符误报。

4. **README** — 项目名、一句话概述、快速开始（安装 / 最小示例 / 开发命令）。

5. **本地质量门** — 写入 `.pre-commit-config.yaml`（家族标准）：

   ```yaml
   repos:
     - repo: https://github.com/pre-commit/pre-commit-hooks
       rev: v5.0.0
       hooks:
         - id: check-ast
         - id: check-toml
         - id: check-yaml
         - id: check-json
         - id: check-merge-conflict
         - id: check-case-conflict
         - id: end-of-file-fixer
           exclude: '\.py$'
         - id: trailing-whitespace
           exclude: '\.py$'

     - repo: https://github.com/astral-sh/ruff-pre-commit
       rev: v0.12.7
       hooks:
         - id: ruff-check
           args: ["--fix"]
           files: ^(src|tests)/
         - id: ruff-format
           files: ^(src|tests)/

     - repo: https://github.com/RobertCraigie/pyright-python
       rev: v1.1.403
       hooks:
         - id: pyright
           args: ["--level", "error"]
           files: ^(src|tests)/

     - repo: https://github.com/econchick/interrogate
       rev: 1.7.0
       hooks:
         - id: interrogate
           files: ^src/

     - repo: local
       hooks:
         - id: pytest-cov
           name: pytest coverage
           entry: uv run pytest --cov=<package> --cov-fail-under=90 -q
           language: system
           pass_filenames: false
           always_run: true
           types: [python]

         # 防漂移：静态规则必须与 agent-kit 模板一致（步骤 6 安装 agent-kit 后生效）
         - id: agent-kit-check
           name: agent-kit drift check
           entry: uv run agent-kit update --check
           language: system
           pass_filenames: false
           always_run: true
   ```

   然后安装依赖并挂上钩子：

   ```bash
   uv sync --extra dev && uv run pre-commit install
   ```

6. **接入 agent-kit**（静态规则由模板统一同步，禁止手写 `.agents/`）：

   - 把 `infinity-agent-kit` 加入 dev 依赖（开发期可用 git 源）：

     ```toml
     infinity-agent-kit = { git = "https://github.com/yinbailiang/agent_kit" }
     ```

   - 安装并写入配置：

     ```bash
     uv sync --extra dev
     uv run agent-kit install --target .
     ```

   - 按项目实际修改 `.agents/agent_kit.toml`（toolchain 命令、extras、skills），
     再运行 `uv run agent-kit update` 生效。

7. **配置 CI/CD** — 按 `setup-cicd` 技能创建 `.github/workflows/`。

8. **全量验证与首次提交**：

   ```bash
   uv run pre-commit run --all-files
   git init && git add -A && git commit -m "chore: 初始化项目"
   ```

## 验收清单

- [ ] `uv run pre-commit run --all-files` 全绿（含 agent-kit 防漂移检查）
- [ ] `uv run pyright` 零错误；测试全过且覆盖率达阈值
- [ ] `.agents/` 由 agent-kit 生成，`uv run agent-kit update --check` 无漂移
- [ ] `.github/workflows/` 已就绪，推送后 Actions 自动运行
