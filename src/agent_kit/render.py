"""模板渲染：把 ``{{TOKEN}}`` 占位符替换为项目配置值。

只有全大写下划线形式的占位符（``{{PROJECT_NAME}}``）会被替换；
其余花括号内容（如代码示例中的 ``{{`` / ``}}``）原样保留。
"""

import re

from agent_kit.errors import RenderError

_TOKEN = re.compile(r"\{\{([A-Z][A-Z0-9_]*)\}\}")


def render(text: str, values: dict[str, str]) -> str:
    """替换所有 ``{{TOKEN}}``；出现未定义的占位符时抛出 ``RenderError``。"""

    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        if name not in values:
            raise RenderError(f"模板包含未定义的占位符：{{{{{name}}}}}")
        return values[name]

    return _TOKEN.sub(replace, text)
