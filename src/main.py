"""AI 行业新闻自动抓取并推送到飞书 (MVP 原型)."""

import logging
import sys
import uuid
from datetime import datetime

# Windows 终端 UTF-8 支持
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from src.config import WEBHOOK_URL, RSS_FEEDS
from src.fetcher import fetch_rss
from src.summarizer import summarize
from src.deduplicator import load_seen, deduplicate, save_seen
from src.formatters.feishu_card import FeishuCardFormatter
from src.senders.feishu import FeishuSender
from src.models import RunResult

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def run_pipeline(silent: bool = False) -> RunResult:
    """编排: 抓取 → 去重 → AI 摘要 → 格式化 → 推送 → 保存。返回结构化结果。

    silent=True 时推送失败不发飞书告警 (webapp 手动触发场景)。
    """
    run_id = uuid.uuid4().hex[:12]
    started_at = datetime.now()

    logger.info("=" * 40)
    logger.info("开始执行新闻抓取任务 (run_id=%s)", run_id)

    all_articles = []
    for feed in RSS_FEEDS:
        all_articles.extend(fetch_rss(feed))

    logger.info("共抓取 %d 条新闻", len(all_articles))

    seen = load_seen()
    new_articles = deduplicate(all_articles, seen)
    logger.info(
        "去重后新文章: %d 条 (已推送: %d 条)",
        len(new_articles),
        len(all_articles) - len(new_articles),
    )

    if not new_articles:
        logger.info("无新内容, 跳过本次推送")
        return RunResult(
            run_id=run_id,
            success=True,
            started_at=started_at,
            finished_at=datetime.now(),
            new_article_count=0,
            summary="",
            push_status="skipped",
        )

    summary = summarize(new_articles)

    formatter = FeishuCardFormatter()
    card = formatter.format(summary, new_articles)
    payload = {"msg_type": "interactive", "card": card}

    sender = FeishuSender(WEBHOOK_URL, silent=silent)
    if not sender.is_configured():
        push_status = "skipped"
        push_ok = False
        logger.warning("Webhook 未配置, 跳过推送 (仍会保存去重记录)")
    else:
        push_ok = sender.send(payload)
        push_status = "success" if push_ok else "failed"

    if push_ok or push_status == "skipped":
        save_seen(seen)
        if push_status == "success":
            logger.info("任务完成 ✅")
        else:
            logger.info("任务完成 (无 Webhook) ✅")
        success = True
    else:
        logger.error("任务完成但有错误 ❌")
        success = False

    return RunResult(
        run_id=run_id,
        success=success,
        started_at=started_at,
        finished_at=datetime.now(),
        new_article_count=len(new_articles),
        summary=summary,
        push_status=push_status,
    )


def main() -> None:
    """CLI 入口: 跑一次 pipeline 并按结果返回 exit code。"""
    result = run_pipeline()
    if result.summary:
        print("\n" + result.summary + "\n")
    sys.exit(0 if result.success else 1)


if __name__ == "__main__":
    main()
