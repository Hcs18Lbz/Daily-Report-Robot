# 后端管理页面补全计划

> 状态: 草案, 待 review
> 范围: 全功能 (RSS 源 CRUD + Webhook/API Key 改写 + 推送时间 + 手动触发 + 运行历史)
> 存储: `config.py` + `.env` 持真相源, UI 回写 (用户已确认)
> 鉴权: localhost 独占, 无鉴权 (用户已确认)
> 技术栈: Flask + Jinja + 原生 CSS, 单 Python 进程

---

## 1. 文件变动总览

| 路径 | 状态 | 作用 |
|------|------|------|
| `requirements.txt` | 新增 | `feedparser requests python-dotenv flask` |
| `src/models.py` | 修改 | 新增 `RunResult` dataclass |
| `src/main.py` | 重构 | 旧 `main()` → `run_pipeline(silent=False) -> RunResult`; CLI 入口保留为薄包装 |
| `src/senders/feishu.py` | 修改 | 构造器加 `silent: bool = False`, 静默时不发告警 |
| `src/config.py` | 修改 | 追加 `MORNING_SCHEDULE = "09:00"` / `EVENING_SCHEDULE = "19:00"` 常量 |
| `src/webapp/__init__.py` | 新增 | 空包标记 |
| `src/webapp/app.py` | 新增 | Flask 工厂 + 6 个路由 |
| `src/webapp/config_io.py` | 新增 | RSS / .env / 计划任务 / 调度时间的读写封装 |
| `src/webapp/runner.py` | 新增 | `RunManager` 单例: 单进程线程 + 互斥锁 + 状态文件 |
| `src/webapp/templates/{base,dashboard,feeds,settings,run,history}.html` | 新增 | 6 个 Jinja 模板 |
| `src/webapp/static/style.css` | 新增 | 单文件 ~150 行 |
| `data/runs/<run_id>.json` | 运行时 | 单次运行完整状态 |
| `data/run_history.json` | 运行时 | 历史索引, 最多 50 条 |
| `start-webapp.bat` | 新增 | 激活 venv + `python -m src.webapp.app`, `pause` 保留供双击 |
| `.gitignore` | 修改 | 追加 `data/`、`__pycache__/`、`.venv/` (顺手补全) |
| `AGENTS.md` | 修改 | 加 webapp 段: 启动命令、模块、状态文件位置、并发模型 |
| `README.md` | 修改 | 加 "Web 管理界面" 段, install 段改用 `requirements.txt` |

---

## 2. 架构

```
                     localhost:5000
                            │
                            ▼
                  ┌──────────────────┐
                  │  src/webapp/app  │  Flask 路由 (GET/POST)
                  └────────┬─────────┘
                           │
        ┌──────────────────┼────────────────────┐
        ▼                  ▼                    ▼
  config_io.py        runner.py            (templates + CSS)
  读写 config.py      RunManager
  读写 .env            (threading.Lock)
  PowerShell 同步       │
  Task Scheduler       ▼
                  src/main.run_pipeline
                           │
                  ┌────────┴─────────┐
                  ▼                  ▼
             抓取→去重→摘要      写 data/runs/<id>.json
             →格式化→推送       + 追加 data/run_history.json
```

`run_pipeline()` 一次调用产出 `RunResult`, 状态落盘后 webapp 即可在 `/run/<id>` 轮询。

---

## 3. 关键决策 (为什么这么做)

- **Flask 而非 FastAPI**: 同步模型 + 单进程 + Jinja 模板, 最少脚手架, 符合项目 "白盒避免过度抽象" 风格。
- **`main.py` 暴露 `run_pipeline()` 而非拆出 `pipeline.py`**: 50 行流程拆到独立模块不划算, 改成 module-level 公开函数 + CLI 包装函数即可, 改动最小。
- **静默路径 (`silent=True`)**: 计划任务的失败需要自动告警到飞书群 (现有行为), 手动触发时 UI 已经看到结果, 告警是噪音。`FeishuSender` 加 `silent` 参数。
- **单进程线程 + 锁**: 个人本地使用, 不需要 subprocess 隔离。`threading.Lock` 防止 "立即推送" 与 "计划任务撞车" (虽然计划任务是新进程, 但同机撞车时锁会拒绝并提示)。
- **状态落盘到 JSON 而非 SQLite**: 5 个文件以内的状态量, 没必要引数据库; 与现有 `seen.json` 风格一致。
- **写 `config.py` 用 `tokenize` 局部替换**: 用 `ast.parse + ast.unparse` 会丢注释和分隔线; `tokenize` 能定位 `RSS_FEEDS = [` 到匹配的 `]` 区间, 仅替换 value 部分, 文件其余内容字节不变。
- **调度时间双源**: `config.py` 是逻辑真相 (UI 改这里), 启动 webapp 时用 `Register-ScheduledTask -Force` 把它同步到 Task Scheduler。Dashboard 显示的 "NextRun" 是实时从 Task Scheduler 读, 帮助用户看见真实生效值。
- **写保护**: 写 `config.py` 前自动备份 `config.py.bak`; 写后用 `ast.parse` 校验, 失败回滚。`.env` 用 `dotenv.set_key` 原子写, 不需要额外保护。
- **API Key 在 UI 默认遮蔽**: 编辑时单独弹输入框, 留空表示不改; 写 `.env` 时如果用户留空则跳过那一行。

---

## 4. 模块 / 接口

### 4.1 `src/models.py` (修改)

新增 dataclass:
```python
@dataclass
class RunResult:
    run_id: str
    success: bool
    started_at: datetime
    finished_at: datetime
    new_article_count: int
    summary: str
    push_status: str | None   # "success" | "failed" | "skipped"
    error: str | None
```

### 4.2 `src/main.py` (重构)

```python
def run_pipeline(silent: bool = False) -> RunResult:
    """编排: 抓取→去重→摘要→格式化→推送→保存。返回结构化结果。"""

def main() -> None:  # CLI 包装, 行为不变
    result = run_pipeline()
    print("\n" + result.summary + "\n")
    sys.exit(0 if result.success else 1)

if __name__ == "__main__":
    main()
```

`run_id` 在入口处用 `uuid.uuid4().hex[:12]` 生成; `silent` 透传给 `FeishuSender`。

### 4.3 `src/senders/feishu.py` (修改)

```python
class FeishuSender(Sender):
    def __init__(self, webhook_url: str, silent: bool = False) -> None:
        self.webhook_url = webhook_url
        self.silent = silent

    def send(self, payload: dict) -> bool:
        ...
        if not result.get("code") == 0:
            if not self.silent:
                self._send_alert(...)
            return False
        ...

    def _send_alert(self, error_msg: str) -> None:
        if self.silent:
            return
        ...
```

### 4.4 `src/webapp/runner.py` (新增)

```python
class RunManager:
    """进程内单例。lock 互斥; 状态写到 data/runs/<id>.json。"""

    def trigger(self) -> str:           # 成功返回 run_id; 已有运行中则 raise ConflictError
    def get_status(self, run_id: str) -> dict
    def list_history(self, limit: int = 50) -> list[dict]
    def get_run_detail(self, run_id: str) -> dict | None
```

- 模块加载时实例化单例: `manager = RunManager()`。
- `_execute(run_id)` 调 `run_pipeline(silent=True)`, 把 `RunResult` 落到 `data/runs/<run_id>.json`, 追加 `data/run_history.json` (capped 50)。
- 异常分支: 任何 unhandled exception 也写 `status: failed` + `error: traceback`, 保证前端永远拿到终态。

### 4.5 `src/webapp/config_io.py` (新增)

```python
def read_rss_feeds() -> list[dict[str, str]]
def write_rss_feeds(new_feeds: list[dict[str, str]]) -> None
    # 写前 cp config.py config.py.bak
    # tokenize 定位 RSS_FEEDS = [  到匹配的 ]
    # 替换为新 list literal
    # ast.parse 校验, 失败回滚到 .bak

def read_env(key: str) -> str           # 用 dotenv_values
def write_env(key: str, value: str) -> None   # 用 set_key, 原子

def read_schedule() -> dict[str, str]   # {"morning": "09:00", "evening": "19:00"}
def write_schedule(morning: str, evening: str) -> None
    # 先用 PowerShell 调 Register-ScheduledTask -Force
    # 失败抛错 (UI 不写 config.py)
    # 成功才写 config.py:MORNING/EVENING_SCHEDULE

def get_next_run_times() -> dict[str, datetime | None]
    # PowerShell 查 AI-News-Morning / AI-News-Evening 的 NextRunTime
```

校验: RSS 源 name/URL 非空, URL 以 `http` 开头; 推送时间格式 `^([01]\d|2[0-3]):[0-5]\d$`。

### 4.6 `src/webapp/app.py` (新增)

| 路由 | 方法 | 功能 |
|------|------|------|
| `/` | GET | Dashboard: 概览 + 立即推送按钮 + 最近 5 次 |
| `/feeds` | GET | 列表 |
| `/feeds/new` | GET | 新增表单 |
| `/feeds/<idx>/edit` | GET | 编辑表单 |
| `/feeds/<idx>/delete` | POST | 删除 (idx 来自列表顺序) |
| `/feeds/save` | POST | 统一保存 (新增/编辑) |
| `/settings` | GET / POST | Webhook/Key/时间 表单 |
| `/run` | POST | 手动触发, 返回 `{run_id, status: "queued"}` |
| `/run/<run_id>` | GET | 详情页 (前端 2s 轮询 `/run/<id>/status`) |
| `/run/<run_id>/status` | GET | JSON, 供轮询 |
| `/history` | GET | 历史列表 |

模板: `base` / `dashboard` / `feeds` / `settings` / `run` / `history`。
- `run.html` 内嵌 ~10 行 vanilla JS (`setInterval(fetch, 2000)`), 无依赖。
- 错误处理: 校验失败返回表单页 + 顶部错误条; 内部异常返回 500 + 文案。

### 4.7 `templates/` & `static/style.css`

- 6 个 Jinja 模板, 全部继承 `base.html` (顶部导航 + 底部时间戳)。
- 单 CSS 文件, 不引外部库; 浅色主题, 表格用 `<table>`, 表单用原生 `<form>` + `<input>`。

---

## 5. 数据 / 状态 schema

### `data/runs/<run_id>.json`
```json
{
  "run_id": "a1b2c3d4e5f6",
  "started_at": "2026-06-02T16:17:05",
  "finished_at": "2026-06-02T16:17:34",
  "status": "success",
  "new_article_count": 10,
  "summary": "【核心资讯汇总】今日 AI 领域聚焦...",
  "push_status": "success",
  "error": null,
  "trigger": "manual"
}
```

### `data/run_history.json`
```json
{
  "runs": [
    {"run_id": "a1b2c3d4e5f6", "started_at": "...", "status": "success", "new_article_count": 10, "trigger": "manual"},
    ...
  ]
}
```

`runs` 数组按 `started_at` 倒序, 写入时裁剪到 50 条。

---

## 6. 实施顺序 (每阶段可独立验证)

### 阶段 1: 脚手架
- 写 `requirements.txt`
- 创建 `src/webapp/__init__.py`
- 创建 `data/` 目录
- 写 `start-webapp.bat`
- 改 `.gitignore` (加 `data/`、`__pycache__/`、`.venv/`)
- 跑 `pip install -r requirements.txt` 验证

### 阶段 2: 重构 `main.py` + `FeishuSender`
- `models.py` 加 `RunResult`
- `main.py` 重构, CLI 行为不变
- `senders/feishu.py` 加 `silent`
- 验证: `python -m src.main` 输出与原版一致 (含 `task complete ✅`)

### 阶段 3: `config_io.py`
- 4 组读 / 4 组写函数
- 写单测: 增删 RSS、读写 .env、改 schedule, 事后 `python -c "import src.config"` 加载无异常
- 验证: REPL 调一遍, 肉眼 diff `config.py` / `.env` / Task Scheduler 实际值

### 阶段 4: `runner.py`
- `RunManager` + 状态文件 + history 追加
- 验证: REPL 调 `manager.trigger()`, 看到 `data/runs/<id>.json` 出现且最终 `status: success`, `run_history.json` 多了 1 条

### 阶段 5: Flask app + 模板
- 写模板 + 路由 + CSS
- 启动 `python -m src.webapp.app`
- 验证: 4 个页面渲染无异常, 手动 trigger 在 UI 上能看到状态变化

### 阶段 6: 端到端
走完 "## 7. 验证清单" 所有项。

### 阶段 7: 文档
- `AGENTS.md`: 加 webapp 段 (启动命令、模块、并发模型、data/ 路径)
- `README.md`: 加 "Web 管理界面" 段, 改 install 段用 `requirements.txt`

---

## 7. 验证清单 (端到端, 全部要过)

- [ ] `start-webapp.bat` 启动后 `http://127.0.0.1:5000/` 返回 200
- [ ] `/feeds` 列表与 `src/config.py:RSS_FEEDS` 一致
- [ ] `/feeds` 新增一个源 → `config.py` 同步, `python -c "from src.config import RSS_FEEDS"` 能加载
- [ ] `/feeds` 删除一个源 → `config.py` 同步, 无残留
- [ ] `/feeds` 提交空 name 或非 http URL → 表单页顶部红条报错, `config.py` 不变
- [ ] `/settings` 改 Webhook URL → `.env` 同步, 留空 API Key 时 `.env` 的 `NVIDIA_API_KEY` 不动
- [ ] `/settings` 把早间时间改为 `10:00` → `config.py:MORNING_SCHEDULE == "10:00"`, `Get-ScheduledTask AI-News-Morning` 触发器时间变 `10:00`
- [ ] 立即推送按钮 → `/run/<id>` 状态从 `queued → running → success` 真实变化, 飞书群收到卡片
- [ ] 立即推送运行时再点一次 → 第二次 409, UI 提示 "上一次推送未结束"
- [ ] `/history` 列出最近运行, 倒序, 不超过 50 条
- [ ] 立即 `python -m src.main` 仍然正常 (CLI 入口未坏)
- [ ] `config.py.bak` 在写操作后存在, 内容是写之前的版本
- [ ] 写坏一次 (手动构造一个非法 list), 走完流程后 `config.py` 仍是上一次成功的版本 (回滚生效)
- [ ] `AGENTS.md` 和 `README.md` 已同步

---

## 8. 风险与权衡

- **`config.py` 写回复杂度**: tokenize + 备份 + 校验回滚比纯 ast 替换多 ~30 行。值得: 避免破坏现有注释和格式, 符合 "白盒可读" 风格。
- **单进程并发上限**: `threading.Lock` 拒绝第二次 trigger, 简单清晰。多用户场景下需要换 Redis lock 或 subprocess 隔离, 不在本期。
- **调度时间双源**: 真相在 `config.py`, Task Scheduler 是执行副本。重启 webapp 时主动用 `config.py` 重新 `Register-ScheduledTask -Force` 一次, 保证不漂移。
- **`data/` 不入 git**: 部署/迁移需手工复制, 容易丢历史。后续可考虑加 `data/runs/` 入 git 但 `data/run_history.json` 不入 (历史是本地视角)。
- **LLM 调用阻塞 HTTP 线程**: Flask dev server 是多线程, `run_pipeline()` 在 worker 线程跑 30~60s, 其他请求不受影响。如果用户量上来考虑 `flask run --threads 1` 或换 waitress。
- **测试覆盖**: 0 个测试, 与 `AGENTS.md` 现状一致; 写本功能也不补 pytest, 保持 "避免过度抽象" 风格。验证靠 `## 7` 清单的手动跑通。
