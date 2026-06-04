# AI 行业资讯自动化推送

> 自动化 RSS 新闻抓取 → AI 摘要 → 飞书定时推送

## 功能特性

- **多源聚合**: 聚合 OpenAI、TechCrunch、VentureBeat 等 6 个优质 AI 资讯源
- **AI 简报**: 调用 NVIDIA NIM (Qwen 3.5 122B) 生成结构化新闻简报
- **智能去重**: 自动过滤已推送内容，早晚推送不重复
- **定时推送**: 每天 09:00 和 19:00 自动推送至飞书群
- **失败告警**: 推送异常时自动发送告警通知
- **模块化架构**: 高内聚低耦合，易于扩展新源和新推送渠道

## 快速开始

### 1. 环境要求

- Python 3.10+
- 飞书群自定义机器人 Webhook URL
- NVIDIA NIM API Key (免费申请: https://build.nvidia.com/)

### 2. 安装依赖

```bash
# 创建虚拟环境
python -m venv .venv

# 激活环境 (Windows)
.\.venv\Scripts\activate

# 安装依赖
pip install feedparser requests python-dotenv
```

### 3. 配置环境变量

复制 `.env.example` 为 `.env` 并填入真实值：

```env
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/你的webhook
NVIDIA_API_KEY=nvapi-你的api_key
```

### 4. 手动运行

```bash
.\.venv\Scripts\activate
python -m src.main
```

## 定时推送

### Windows 任务计划

项目提供两个快捷脚本：

| 脚本 | 作用 |
|------|------|
| `start-tasks.bat` | 注册定时任务 (09:00 + 19:00) |
| `stop-tasks.bat` | 删除定时任务 |
| `run.bat` | 手动执行一次推送 |

双击 `start-tasks.bat` 即可开启自动推送。

**注意**: 任务依赖电脑开机状态。如需 24/7 运行，建议部署到服务器或使用 GitHub Actions。

## 项目结构

```
Daily-Report-Robot/
├── src/
│   ├── __init__.py
│   ├── config.py           # 配置 + RSS 源定义
│   ├── models.py           # Article 数据类
│   ├── fetcher.py          # RSS 抓取模块
│   ├── summarizer.py       # NVIDIA LLM 摘要
│   ├── deduplicator.py     # 去重逻辑 (seen.json)
│   ├── formatters/
│   │   ├── base.py         # Formatter 接口
│   │   └── feishu_card.py  # 飞书卡片实现
│   ├── senders/
│   │   ├── base.py         # Sender 接口
│   │   └── feishu.py       # 飞书 Webhook 实现
│   └── main.py             # 入口编排
├── tests/                  # 测试目录 (待补充)
├── .env                    # 环境变量 (不提交)
├── .gitignore
├── run.bat                 # 手动运行脚本
├── start-tasks.bat         # 注册定时任务
├── stop-tasks.bat          # 删除定时任务
└── README.md
```

## 配置说明

### 添加/删除 RSS 源

编辑 `src/config.py` 中的 `RSS_FEEDS`：

```python
RSS_FEEDS = [
    {"name": "源名称", "url": "https://example.com/feed.xml"},
    # 添加新源...
]
```

### 调整推送频率

编辑 `start-tasks.bat` 中的时间参数：

```powershell
$trigger1 = New-ScheduledTaskTrigger -Daily -At "09:00"  # 修改时间
```

## 常见问题

**Q: 推送失败怎么办？**
A: 检查 `.env` 中的 Webhook URL 和 API Key 是否正确。失败时飞书群会收到告警通知。

**Q: 某些 RSS 源抓不到内容？**
A: 部分源可能限流或格式不标准。日志会输出警告，不影响其他源。

**Q: 如何重置去重记录？**
A: 删除项目根目录的 `seen.json` 文件即可。

## 技术栈

- **RSS 解析**: feedparser
- **HTTP 请求**: requests
- **AI 摘要**: NVIDIA NIM API (Qwen 3.5 122B)
- **推送**: 飞书自定义机器人 Webhook
- **调度**: Windows 任务计划程序

## License

MIT
