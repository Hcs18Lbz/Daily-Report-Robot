"""RSS 抓取模块。"""

import logging

import feedparser
import requests

from src.models import Article
from src.config import MAX_ENTRIES_PER_FEED, REQUEST_TIMEOUT

logger = logging.getLogger(__name__)


def fetch_rss(feed: dict[str, str]) -> list[Article]:
    """抓取单个 RSS 源，返回文章列表。"""
    logger.info("正在抓取: %s", feed["name"])
    try:
        resp = requests.get(feed["url"], timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        parsed = feedparser.parse(resp.content)

        if not parsed.entries:
            logger.warning("  → 无内容: %s", feed["name"])
            return []

        articles = [
            Article(
                source=feed["name"],
                title=entry.get("title", "无标题"),
                link=entry.get("link", ""),
                published=entry.get("published", ""),
                description=_clean_desc(entry),
            )
            for entry in parsed.entries[:MAX_ENTRIES_PER_FEED]
        ]
        logger.info("  → 获取 %d 条", len(articles))
        return articles

    except requests.RequestException as e:
        logger.error("  → 网络错误: %s — %s", feed["name"], e)
        return []
    except Exception as e:
        logger.error("  → 解析失败: %s — %s", feed["name"], e)
        return []


def _clean_desc(entry) -> str:
    """从 feedparser entry 中提取并清理描述文本。"""
    desc = entry.get("summary", "") or entry.get("description", "")
    # 简单去除 HTML 标签
    clean = ""
    in_tag = False
    for ch in desc:
        if ch == "<":
            in_tag = True
        elif ch == ">":
            in_tag = False
        elif not in_tag:
            clean += ch
    return clean[:300]
