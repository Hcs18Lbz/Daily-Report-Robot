"""数据模型定义。"""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class Article:
    """一条新闻文章。"""
    source: str
    title: str
    link: str
    published: str
    description: str = ""


@dataclass
class RunResult:
    """一次 pipeline 运行的结构化结果, 供 CLI 与 webapp 共用。"""
    run_id: str
    success: bool
    started_at: datetime
    finished_at: datetime
    new_article_count: int
    summary: str
    push_status: str | None
    error: str | None = None
