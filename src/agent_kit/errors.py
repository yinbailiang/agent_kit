"""agent_kit 的错误体系：所有操作失败均抛出 ``AgentKitError`` 的子类。"""


class AgentKitError(Exception):
    """agent_kit 操作失败的基类。"""


class ConfigError(AgentKitError):
    """项目配置缺失或无效。"""


class RenderError(AgentKitError):
    """模板渲染失败（如出现未定义的占位符）。"""
