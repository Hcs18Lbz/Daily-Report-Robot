# 如何探索新的资讯领域

> 最后更新: 2026-04-03

## 场景

当前项目推送的是 **AI 行业资讯**。如果你想新增一个独立领域（如"金融资讯"、"科技早报"），按以下步骤操作。

---

## 方案一：合并到现有推送 (简单)

适合：新领域文章不多，想和 AI 资讯一起推。

### 操作
直接在 `src/config.py` 的 `RSS_FEEDS` 中添加新领域的源：

```python
RSS_FEEDS = [
    # AI 相关
    {"name": "OpenAI Blog", "url": "..."},
    # 新领域
    {"name": "36Kr", "url": "https://36kr.com/feed"},
    {"name": "少数派", "url": "https://sspai.com/feed"},
]
```

### 效果
- 新领域的文章会混入 AI 资讯一起推送
- AI 摘要会自动识别并分类
- 去重机制对所有源一视同仁

### 缺点
- 领域混杂，AI 分类可能不够精准
- 无法独立控制推送时间和频率

---

## 方案二：独立推送通道 (推荐)

适合：新领域有独立的关注群体，需要单独推送。

### 1. 创建新模块目录
```
Daily-Report-Robot/
├── src/              # AI 资讯 (现有)
├── finance/          # 新: 金融资讯
│   ├── config.py     # 金融专属配置
│   └── main.py       # 复用 src 的模块
```

### 2. 编写 finance/config.py
```python
"""金融资讯配置。"""
import os
from dotenv import load_dotenv
load_dotenv()

WEBHOOK_URL = os.environ.get("FINANCE_WEBHOOK_URL", "")  # 金融群的 Webhook
NVIDIA_API_KEY = os.environ.get("NVIDIA_API_KEY", "")

LLM_MODEL = "qwen/qwen3.5-122b-a10b"
MAX_ENTRIES_PER_FEED = 5
REQUEST_TIMEOUT = 10

RSS_FEEDS = [
    {"name": "36Kr", "url": "https://36kr.com/feed"},
    {"name": "财联社", "url": "https://www.cls.cn/rss"},
]
```

### 3. 编写 finance/main.py
```python
"""金融资讯推送入口。"""
import sys; sys.path.append("..")  # 复用 src 模块
import logging
from src.config import NVIDIA_API_KEY
from finance.config import WEBHOOK_URL, RSS_FEEDS
from src.fetcher import fetch_rss
from src.summarizer import summarize
from src.deduplicator import load_seen, deduplicate, save_seen
from src.formatters.feishu_card import FeishuCardFormatter
from src.senders.feishu import FeishuSender

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def main():
    logger.info("开始执行金融资讯推送")
    all_articles = []
    for feed in RSS_FEEDS:
        all_articles.extend(fetch_rss(feed))

    seen = load_seen()
    new_articles = deduplicate(all_articles, seen)
    if not new_articles:
        logger.info("无新内容，跳过")
        return

    summary = summarize(new_articles)
    formatter = FeishuCardFormatter()
    card = formatter.format(summary, new_articles)
    sender = FeishuSender(WEBHOOK_URL)
    success = sender.send({"msg_type": "interactive", "card": card})
    if success:
        save_seen(seen)
        logger.info("金融推送完成 ✅")

if __name__ == "__main__":
    main()
```

### 4. 添加环境变量
在 `.env` 中添加金融群的 Webhook：
```env
FINANCE_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/金融群的hook
```

### 5. 创建独立运行脚本
新建 `run-finance.bat`：
```batch
@echo off
cd /d <YOUR_PROJECT_DIR>
call .venv\Scripts\activate
python -m finance.main
```

### 6. 注册独立定时任务
```powershell
$action = New-ScheduledTaskAction -Execute "<YOUR_PROJECT_DIR>\run-finance.bat"
$trigger = New-ScheduledTaskTrigger -Daily -At "08:30"  # 金融早报可更早
Register-ScheduledTask -TaskName "Finance-News-Morning" -Action $action -Trigger $trigger -Force
```

---

## 方案三：多频道推送 (高级)

适合：一个群需要同时推送多个领域。

### 思路
在 `main.py` 中循环多个配置，每个领域生成一张卡片，依次发送到同一个群。

```python
DOMAINS = [
    {"name": "AI", "feeds": [...], "webhook": "..."},
    {"name": "金融", "feeds": [...], "webhook": "..."},
    {"name": "科技", "feeds": [...], "webhook": "..."},
]

for domain in DOMAINS:
    # 对每个领域执行: 抓取 → 去重 → 摘要 → 推送
```

---

## 选择建议

| 场景 | 推荐方案 |
|------|----------|
| 只是多几个源 | 方案一 (合并) |
| 独立领域 + 独立群 | 方案二 (独立模块) |
| 一个群多个领域 | 方案三 (多频道) |
