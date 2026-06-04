"""飞书卡片消息格式化器。"""

from datetime import datetime

from src.models import Article
from src.formatters.base import Formatter


class FeishuCardFormatter(Formatter):
    """将 AI 摘要 + 参考文献格式化为飞书卡片 JSON。"""

    def format(self, summary: str, articles: list[Article]) -> dict:
        today = datetime.now().strftime("%Y-%m-%d")
        now = datetime.now().strftime("%H:%M")

        refs_md = self._build_references(articles)

        elements: list[dict] = [
            {"tag": "div", "text": {"content": f"**{today}**\n\n{summary}", "tag": "lark_md"}},
        ]

        # 如果 LLM 输出的 summary 里已经包含延伸阅读，就不重复添加
        if refs_md and "延伸阅读" not in summary and "阅读原文" not in summary:
            elements.append({"tag": "hr"})
            elements.append({"tag": "div", "text": {"content": f"**📎 信息来源**\n\n{refs_md}", "tag": "lark_md"}})

        elements.append({"tag": "hr"})
        elements.append({"tag": "note", "elements": [{"tag": "plain_text", "content": f"由 AI 生成 | {now}"}]})

        return {
            "config": {"wide_screen_mode": True},
            "header": {"template": "blue", "title": {"content": "📰 AI 行业资讯", "tag": "plain_text"}},
            "elements": elements,
        }

    @staticmethod
    def _build_references(articles: list[Article]) -> str:
        ref_lines = []
        for i, a in enumerate(articles, 1):
            link_md = f"[阅读原文]({a.link})" if a.link else ""
            ref_lines.append(f"**{i}. {a.title}**  —  {a.source}  {link_md}\n")
        return "\n".join(ref_lines)
