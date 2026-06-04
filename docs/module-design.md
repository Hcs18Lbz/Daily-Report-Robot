# 模块详细设计

> 最后更新: 2026-04-03

## models.py — Article 数据类

```python
@dataclass
class Article:
    source: str       # 来源名称，如 "OpenAI Blog"
    title: str        # 文章标题
    link: str         # 文章 URL
    published: str    # 发布时间 (RSS 原始字符串)
    description: str  # 摘要内容 (已清理 HTML)
```

**设计决策**: 使用 dataclass 而非 dict，提供类型安全、IDE 补全、不可变语义。

---

## fetcher.py — RSS 抓取

### 核心函数
```python
def fetch_rss(feed: dict[str, str]) -> list[Article]
```

### 流程
1. `requests.get(url, timeout=10)` 获取原始内容
2. `feedparser.parse(content)` 解析 RSS
3. 遍历 entries，构造 Article 对象
4. 异常时返回空列表，不中断主流程

### 错误处理
| 错误类型 | 处理方式 |
|----------|----------|
| 网络超时 | 记录 error 日志，返回 [] |
| HTTP 错误 | 记录 error 日志，返回 [] |
| 解析异常 | 记录 error 日志，返回 [] |
| 无内容 | 记录 warning 日志，返回 [] |

### HTML 清理
`_clean_desc()` 手动遍历字符去除 HTML 标签，避免引入额外依赖。

---

## deduplicator.py — 去重模块

### 核心函数
```python
def load_seen() -> set[str]           # 加载已推送记录
def deduplicate(articles, seen)       # 过滤重复，返回新文章
def save_seen(seen)                   # 保存记录 (最多 2000 条)
```

### 去重算法
```
hash = MD5(title.lower() + link.lower())[:12]
```

**为什么用 title + link**: 同一篇文章在不同 RSS 源中 title 可能略有差异，但 link 通常一致。两者组合可避免误判。

### seen.json 格式
```json
{
  "seen": ["abc123def456", "789xyz012abc", ...]
}
```

**容量控制**: 超过 2000 条时自动裁剪最旧的记录。

---

## summarizer.py — AI 摘要

### 核心函数
```python
def summarize(articles: list[Article]) -> str
```

### API 调用
- **端点**: `https://integrate.api.nvidia.com/v1/chat/completions`
- **模型**: `qwen/qwen3.5-122b-a10b`
- **超时**: 60 秒
- **温度**: 0.3 (低随机性，保证输出稳定)

### Prompt 设计
要求 LLM 输出以下格式：
```
【核心资讯汇总】一句话总览
一、板块标题
1. **新闻标题**: 详细内容 (50-100字，含关键数据)
二、板块标题
...
【延伸阅读】
[1] 标题 → 链接
```

### 降级策略
| 情况 | 返回内容 |
|------|----------|
| 无文章 | "今日暂无新内容。" |
| 无 API Key | "⚠️ 未配置 API Key..." |
| API 超时/失败 | "⚠️ 摘要生成失败..." |

---

## feishu_card.py — 飞书卡片格式化

### 核心类
```python
class FeishuCardFormatter(Formatter):
    def format(summary: str, articles: list[Article]) -> dict
```

### 卡片结构
```
┌─ 📰 AI 行业资讯 (蓝色头) ─────────┐
│  2026-04-03                       │
│                                   │
│  【核心资讯汇总】...               │
│  一、板块标题                      │
│  1. **标题**: 详细内容             │
│  ...                              │
│  ─────────────────                │
│  **参考文献**                     │
│  **1. 文章标题** — 来源 [阅读原文] │
│  ...                              │
│  ─────────────────                │
│  由 AI 生成 | 15:30               │
└───────────────────────────────────┘
```

### 智能判断
如果 LLM 输出的 summary 已包含"延伸阅读"，则不重复添加参考文献区块。

---

## feishu.py — 飞书推送

### 核心类
```python
class FeishuSender(Sender):
    def send(payload: dict) -> bool
    def _send_alert(error_msg: str) -> None  # 内部告警
```

### 告警机制
推送失败时自动发送纯文本告警：
```
⚠️ AI 新闻推送告警
时间: 2026-04-03 15:30
错误: 飞书返回错误: {...}
请检查 run.bat 日志。
```

---

## main.py — 入口编排

仅负责流程编排，不包含业务逻辑：
```
抓取 → 去重 → 判断有无新内容 → AI 摘要 → 格式化 → 推送 → 保存记录
```
