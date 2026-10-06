"""模板渲染测试。"""

import pytest

from agent_kit.errors import RenderError
from agent_kit.render import render


def test_render_substitutes_tokens() -> None:
    assert render("Hi {{NAME}}!", {"NAME": "agent"}) == "Hi agent!"


def test_render_leaves_single_braces_and_other_content() -> None:
    text = "模板 `{}`、字面 `{{` 与 `}}`、小写 `{{name}}` 均保持不变"
    assert render(text, {}) == text


def test_render_rejects_undefined_token() -> None:
    with pytest.raises(RenderError, match="PROJECT_NAME"):
        render("{{PROJECT_NAME}}", {})
