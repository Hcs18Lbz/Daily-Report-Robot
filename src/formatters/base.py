"""消息格式化接口定义。"""

from typing import Protocol

from src.models import Article


class Formatter(Protocol):
    """消息格式化器接口。"""

    def format(self, summary: str, articles: list[Article]) -> dict:
        """将摘要和文章列表格式化为推送消息结构。"""
        ...
