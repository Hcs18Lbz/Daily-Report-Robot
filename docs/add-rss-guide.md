# 如何添加新的 RSS 源

> 最后更新: 2026-04-03

## 快速添加 (30 秒)

### 1. 编辑配置

打开 `src/config.py`，找到 `RSS_FEEDS` 列表：

```python
RSS_FEEDS: list[dict[str, str]] = [
    {"name": "OpenAI Blog", "url": "https://openai.com/blog/rss.xml"},
    {"name": "TechCrunch AI", "url": "https://techcrunch.com/category/artificial-intelligence/feed/"},
    # ... 现有源 ...
    {"name": "新源名称", "url": "https://example.com/feed.xml"},  # ← 添加这行
]
```

### 2. 验证

```bash
.\.venv\Scripts\activate
python -m src.main
```

查看日志输出，确认新源显示 `→ 获取 X 条`。

---

## 如何找到 RSS 地址

### 方法一：网站常见路径
大多数网站的 RSS/XML 地址在以下位置：
- `https://网站.com/feed`
- `https://网站.com/feed.xml`
- `https://网站.com/rss`
- `https://网站.com/rss.xml`
- `https://网站.com/分类名/feed/`

### 方法二：查看网页源码
在目标网站按 `Ctrl + U` 查看源码，搜索 `rss` 或 `atom`：
```html
<link rel="alternate" type="application/rss+xml" href="https://example.com/feed.xml">
```

### 方法三：使用 RSSHub
[RSSHub](https://docs.rsshub.app/) 可为无 RSS 的网站生成订阅源：
```
https://rsshub.app/36kr
https://rsshub.app/github/trending/daily/python
```

### 方法四：Python 快速验证
```python
import feedparser, requests

url = "https://example.com/feed.xml"
r = requests.get(url, timeout=10)
p = feedparser.parse(r.content)
print(f"共 {len(p.entries)} 条")
for e in p.entries[:3]:
    print(f"  - {e.title}")
```

---

## 验证清单

添加新源后，确认以下几点：

- [ ] 日志显示 `→ 获取 X 条` (X > 0)
- [ ] 标题和链接正常解析
- [ ] 描述内容不为空
- [ ] 去重正常工作 (重复运行不重复推送)

---

## 常见问题

**Q: 添加后显示 0 条？**
A: RSS 地址可能不正确，或该网站不使用标准 RSS 格式。尝试其他路径或使用 RSSHub。

**Q: 标题出现乱码？**
A: RSS 编码与 feedparser 解析不匹配。通常是网站问题，不影响其他源。

**Q: 某个源总是超时？**
A: 可能是国内访问境外源的网络问题。可考虑替换为国内可用源，或增加 `REQUEST_TIMEOUT`。
