# SKILL: 配置 GitHub CI/CD

**触发**：CI、CD、CI/CD、GitHub Actions、workflow、流水线、持续集成、自动发布。

## 概览

```text
.github/workflows/
├── test.yml      # 质量门：pre-commit（含静态规则防漂移）+ 多平台测试矩阵
└── publish.yml   # 发布：构建产物 → GitHub Release → PyPI（v* 标签触发）
```

## 前提

- git 仓库已关联 GitHub `origin`（否则 Actions 不会运行）
- 已执行 `uv run pre-commit install` 且 `.pre-commit-config.yaml` 可用
  （见 `init-project` 技能）
- `pyproject.toml` 定义 `test` extra（pytest + pytest-cov）
- 需要发布 PyPI 时：已在 PyPI 注册 Trusted Publisher（步骤 3）

## 步骤

1. **创建 `.github/workflows/test.yml`**：

   ```yaml
   name: Test

   on:
     push:
       branches: [main, master]
     pull_request:
       branches: [main, master]

   jobs:
     pre-commit:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v4

         - name: Install uv
           uses: astral-sh/setup-uv@v5

         - name: Set up Python
           run: uv python install 3.12

         - name: Install dev dependencies
           run: uv sync --extra dev

         - name: Run pre-commit
           run: uv run pre-commit run --all-files

     test:
       needs: pre-commit
       runs-on: ${{ matrix.os }}
       strategy:
         fail-fast: false
         matrix:
           os: [ubuntu-latest, windows-latest, macos-latest]
           python-version: ["3.12", "3.13", "3.14"]

       steps:
         - uses: actions/checkout@v4

         - name: Install uv
           uses: astral-sh/setup-uv@v5

         - name: Set up Python ${{ matrix.python-version }}
           run: uv python install ${{ matrix.python-version }}

         - name: Install dependencies
           run: uv sync --extra test

         - name: Run tests with coverage
           run: uv run pytest --cov=agent_kit --cov-report=term-missing --cov-fail-under=90 -v
   ```

   > 矩阵按 `requires-python` 调整：至少覆盖下界与最新版（示例为 3.12–3.14）。

2. **创建 `.github/workflows/publish.yml`**（与 CI 相同的校验 + 构建发布）：

   ```yaml
   name: Publish to PyPI & Release

   on:
     push:
       tags:
         - "v*"

   jobs:
     pre-commit:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v4

         - name: Install uv
           uses: astral-sh/setup-uv@v5

         - name: Set up Python
           run: uv python install 3.12

         - name: Install dev dependencies
           run: uv sync --extra dev

         - name: Run pre-commit
           run: uv run pre-commit run --all-files

     test:
       needs: pre-commit
       runs-on: ${{ matrix.os }}
       strategy:
         fail-fast: false
         matrix:
           os: [ubuntu-latest, windows-latest, macos-latest]
           python-version: ["3.12", "3.13", "3.14"]

       steps:
         - uses: actions/checkout@v4

         - name: Install uv
           uses: astral-sh/setup-uv@v5

         - name: Set up Python ${{ matrix.python-version }}
           run: uv python install ${{ matrix.python-version }}

         - name: Install dependencies
           run: uv sync --extra test

         - name: Run tests with coverage
           run: uv run pytest --cov=agent_kit --cov-report=term-missing --cov-fail-under=90 -v

     # PyPI 发布使用 Trusted Publisher（OIDC），无需 token：
     # 需在 PyPI 项目设置中将本仓库的 publish.yml 注册为受信发布者。
     build-and-publish:
       needs: [test]
       runs-on: ubuntu-latest
       permissions:
         id-token: write
         contents: write

       steps:
         - uses: actions/checkout@v4

         - name: Install uv
           uses: astral-sh/setup-uv@v5

         - name: Set up Python
           run: uv python install 3.12

         - name: Build package
           run: uv build

         - name: Create GitHub Release
           uses: softprops/action-gh-release@v2
           with:
             files: |
               dist/*.whl
               dist/*.tar.gz
             generate_release_notes: true
           env:
             GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

         - name: Publish to PyPI
           run: uv publish
   ```

3. **注册 Trusted Publisher**（仅发布需要）— PyPI 项目 → Settings → Publishing →
   添加受信发布者：GitHub 仓库 + 工作流名 `publish.yml`（环境留空）。

4. **本地预检**（CI 跑相同的门，先确保本地通过）：

   ```bash
   uv run pre-commit run --all-files
   uv run pytest --cov=agent_kit --cov-fail-under=90 -q
   ```

5. **提交并推送** — `test.yml` 自动运行；发布流程见 `publish` 技能
   （推送 `v*` 标签触发）。

## 注意事项

- GitHub Release 由 CI 创建，禁止手动创建
- CI 与本地共用同一把质量门（pre-commit / 覆盖率 / 防漂移），任一端失败均不可放行
- 版本矩阵只写 Python 版本字符串，如需固定补丁版本可在 `requires-python` 中收敛
