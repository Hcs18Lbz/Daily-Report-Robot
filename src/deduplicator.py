"""文章去重模块 — 基于已推送记录过滤。"""

import hashlib
import json
import logging
import os
from pathlib import Path

from src.models import Article

logger = logging.getLogger(__name__)

# 状态文件路径（与 main.py 同级）
_SEEN_FILE = Path(__file__).parent.parent / "seen.json"
_MAX_SEEN = 2000  # 最多保留 2000 条，防止文件无限增长


def _article_hash(article: Article) -> str:
    """基于 title + link 生成唯一 hash。"""
    raw = f"{article.title.strip().lower()}{article.link.strip().lower()}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()[:12]


def load_seen() -> set[str]:
    """加载已推送文章 hash 集合。"""
    if not _SEEN_FILE.exists():
        return set()
    try:
        with open(_SEEN_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return set(data.get("seen", []))
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("读取 seen.json 失败: %s，从空集合开始", e)
        return set()


def save_seen(seen: set[str]) -> None:
    """保存已推送记录，保留最近 MAX_SEEN 条。"""
    seen_list = sorted(seen)[-_MAX_SEEN:]
    try:
        with open(_SEEN_FILE, "w", encoding="utf-8") as f:
            json.dump({"seen": seen_list}, f, ensure_ascii=False, indent=2)
        logger.info("已保存 %d 条去重记录", len(seen_list))
    except OSError as e:
        logger.error("保存 seen.json 失败: %s", e)


def deduplicate(articles: list[Article], seen: set[str]) -> list[Article]:
    """过滤掉已推送的文章，返回新文章列表。"""
    new_articles = []
    for a in articles:
        h = _article_hash(a)
        if h not in seen:
            seen.add(h)
            new_articles.append(a)
    return new_articles
