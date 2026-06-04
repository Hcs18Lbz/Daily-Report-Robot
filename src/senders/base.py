"""消息推送接口定义。"""

from typing import Protocol


class Sender(Protocol):
    """消息推送器接口。"""

    def is_configured(self) -> bool:
        """是否已正确配置, 未配置时 send 不会真正发送。"""
        ...

    def send(self, payload: dict) -> bool:
        """发送消息，返回是否成功。"""
        ...
