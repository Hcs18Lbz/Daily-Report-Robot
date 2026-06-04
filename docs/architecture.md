# 项目架构

> 最后更新: 2026-04-03

## 系统概览

```
┌─────────────┐     ┌──────────────┐     ┌───────────────┐     ┌────────────┐
│  RSS 源 (6) │────▶│  RSS 抓取    │────▶│   去重过滤     │────▶│ AI 摘要    │
│             │     │  fetcher.py  │     │ deduplicator   │     │ summarizer │
└─────────────┘     └──────────────┘     └───────────────┘     └──────┬─────┘
                                                                      │
┌─────────────┐     ┌──────────────┐     ┌───────────────┐     ┌──────▼─────┐
│  飞书群推送  │◀────│  消息发送    │◀────│  卡片格式化    │◀────│ 新闻简报   │
│  feishu.py │     │  Sender      │     │  Formatter     │     │ (LLM输出)  │
└─────────────┘     └──────────────┘     └───────────────┘     └────────────┘
```

## 数据流

```
1. config.py 定义 RSS_FEEDS 列表
2. fetcher.py 遍历抓取 → 返回 list[Article]
3. deduplicator.py 对比 seen.json → 过滤已推送 → 返回新文章
4. summarizer.py 调用 NVIDIA API → 返回新闻简报文本
5. feishu_card.py 将简报 + 参考文献 → 飞书卡片 JSON
6. feishu.py 发送卡片 → 失败时发送告警纯文本
7. 推送成功 → 更新 seen.json
```

## 目录结构

```
Daily-Report-Robot/
├── src/
│   ├── config.py           # 唯一配置入口: 环境变量 + RSS 源 + 常量
│   ├── models.py           # Article 数据类 (所有模块共享)
│   ├── fetcher.py          # RSS 抓取 (feedparser + requests)
│   ├── summarizer.py       # AI 摘要 (NVIDIA NIM API)
│   ├── deduplicator.py     # 去重逻辑 (MD5 hash + seen.json)
│   ├── formatters/
│   │   ├── base.py         # Formatter Protocol 接口
│   │   └── feishu_card.py  # 飞书卡片实现
│   ├── senders/
│   │   ├── base.py         # Sender Protocol 接口
│   │   └── feishu.py       # 飞书 Webhook 实现 (含告警)
│   └── main.py             # 入口编排 (约 50 行)
├── docs/                   # 项目文档
├── tests/                  # 测试目录
├── .env                    # 环境变量 (不提交)
├── seen.json               # 去重记录 (自动生成)
├── run.bat                 # 手动运行
├── start-tasks.bat         # 注册定时任务
└── stop-tasks.bat          # 删除定时任务
```

## 模块职责

| 模块 | 职责 | 输入 | 输出 |
|------|------|------|------|
| `config.py` | 配置加载 | `.env` 文件 | 常量 + RSS_FEEDS |
| `models.py` | 数据模型 | — | Article 类 |
| `fetcher.py` | RSS 抓取 | feed dict | list[Article] |
| `deduplicator.py` | 去重过滤 | list[Article] + seen set | list[Article] (新) |
| `summarizer.py` | AI 摘要 | list[Article] | 简报文本 |
| `feishu_card.py` | 卡片格式化 | 文本 + 文章列表 | 卡片 dict |
| `feishu.py` | 消息发送 | 卡片 dict | bool (成功/失败) |
| `main.py` | 流程编排 | — | — |

## 扩展点

- **新 RSS 源**: 改 `config.py` 中的 `RSS_FEEDS`
- **新推送渠道**: 在 `senders/` 下新建实现 `Sender` 接口
- **新卡片样式**: 在 `formatters/` 下新建实现 `Formatter` 接口
- **新 AI 模型**: 改 `config.py` 中的 `LLM_MODEL` 或重写 `summarizer.py`
