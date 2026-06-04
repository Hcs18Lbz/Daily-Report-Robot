# AI 行业资讯自动化推送

> 自动化 RSS 新闻抓取 → AI 摘要 → 飞书定时推送 + Web 管理界面

## 功能特性

- **多源聚合**: 聚合 OpenAI、TechCrunch、VentureBeat 等 6 个优质 AI 资讯源
- **AI 简报**: 调用 NVIDIA NIM (Qwen 3.5 122B) 生成结构化新闻简报
- **智能去重**: 自动过滤已推送内容，早晚推送不重复
- **定时推送**: 每天 09:00 和 19:00 自动推送至飞书群
- **失败告警**: 推送异常时自动发送告警通知
- **Web 管理界面**: 浏览器管理 RSS 源、推送配置，手动触发运行，查看历史
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
pip install -r requirements.txt
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

## Web 管理界面

浏览器管理 RSS 源、修改 Webhook/API Key、调整推送时间、手动触发运行、查看历史。

```bash
.\.venv\Scripts\activate
python -m src.webapp.app
```

访问 `http://127.0.0.1:5000/` (localhost 无鉴权)。也可双击 `scripts\start-webapp.bat` 一键启动+自动打开浏览器。

## 定时推送

### Windows 任务计划

项目提供快捷脚本（全部位于 `scripts/`）：

| 脚本 | 作用 |
|------|------|
| `scripts\start-tasks.bat` | 注册定时任务 (09:00 + 19:00) |
| `scripts\stop-tasks.bat` | 删除定时任务 |
| `scripts\run.bat` | 手动执行一次推送 |
| `scripts\start-webapp.bat` | 启动 Web 管理界面 |

双击 `scripts\start-tasks.bat` 即可开启自动推送。

**注意**: 任务依赖电脑开机状态。如需 24/7 运行，建议部署到服务器或使用 GitHub Actions。Web 管理界面启动时会自动同步定时任务时间。

## 项目结构

```
Daily-Report-Robot/
├── scripts/                   # 快捷脚本
│   ├── run.bat                # 手动运行
│   ├── start-tasks.bat        # 注册定时任务
│   ├── stop-tasks.bat         # 删除定时任务
│   └── start-webapp.bat       # 启动 Web 界面
├── src/
│   ├── config.py              # 配置 + RSS 源定义
│   ├── models.py              # Article / RunResult 数据类
│   ├── fetcher.py             # RSS 抓取
│   ├── summarizer.py          # NVIDIA NIM AI 摘要
│   ├── deduplicator.py        # 去重逻辑
│   ├── formatters/
│   │   ├── base.py            # Formatter 接口
│   │   └── feishu_card.py     # 飞书卡片实现
│   ├── senders/
│   │   ├── base.py            # Sender 接口
│   │   └── feishu.py          # 飞书 Webhook 实现
│   ├── main.py                # 入口编排
│   └── webapp/                # Web 管理界面
│       ├── app.py             # Flask 路由
│       ├── config_io.py       # 配置读写
│       ├── runner.py          # 运行管理器
│       ├── templates/         # Jinja2 模板
│       └── static/            # CSS
├── docs/                      # 设计/运维文档
│   ├── architecture.md
│   ├── module-design.md
│   ├── ops-guide.md
│   ├── new-domain-guide.md
│   ├── add-rss-guide.md
│   └── decision-record-news-monitoring.md
├── tests/
│   └── __init__.py
├── .env.example               # 环境变量模板
├── .gitignore
├── requirements.txt
└── README.md
```

## 配置说明

### 添加/删除 RSS 源

编辑 `src/config.py` 中的 `RSS_FEEDS`，或通过 Web 管理界面的 `/feeds` 页面操作：

```python
RSS_FEEDS = [
    {"name": "源名称", "url": "https://example.com/feed.xml"},
]
```

### 调整推送频率

编辑 `scripts\start-tasks.bat` 中的时间参数，或通过 Web 管理界面的 `/settings` 页面调整：

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

**Q: 如何扩展新的推送渠道？**
A: 在 `src/senders/` 下实现 `Sender` 协议，详见 `docs/new-domain-guide.md`。

## 技术栈

- **RSS 解析**: feedparser
- **HTTP 请求**: requests
- **AI 摘要**: NVIDIA NIM API (Qwen 3.5 122B)
- **推送**: 飞书自定义机器人 Webhook
- **调度**: Windows 任务计划程序
- **Web 界面**: Flask + Jinja2

## License

Apache 2.0
