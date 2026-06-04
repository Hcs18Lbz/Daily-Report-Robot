"""配置加载 + RSS 源定义。"""

import os
from dotenv import load_dotenv

load_dotenv()

# ─── 环境变量 ─────────────────────────────────────────────────────────────────

WEBHOOK_URL: str = os.environ.get("FEISHU_WEBHOOK_URL", "")
NVIDIA_API_KEY: str = os.environ.get("NVIDIA_API_KEY", "")

# ─── 常量 ─────────────────────────────────────────────────────────────────────

LLM_MODEL: str = "qwen/qwen3.5-122b-a10b"
MAX_ENTRIES_PER_FEED: int = 5
REQUEST_TIMEOUT: int = 10
MORNING_SCHEDULE: str = "09:00"
EVENING_SCHEDULE: str = "19:00"

RSS_FEEDS: list[dict[str, str]] = [
    {"name": "OpenAI Blog", "url": "https://openai.com/blog/rss.xml"},
    {"name": "TechCrunch AI", "url": "https://techcrunch.com/category/artificial-intelligence/feed/"},
    {"name": "VentureBeat AI", "url": "https://venturebeat.com/category/ai/feed/"},
    {"name": "Ars Technica AI", "url": "https://arstechnica.com/tag/artificial-intelligence/feed/"},
    {"name": "arXiv AI", "url": "https://rss.arxiv.org/rss/cs.AI+cs.LG"},
    {"name": "HackerNews AI", "url": "https://hnrss.org/newest?q=AI+OR+LLM&count=10"},
]
