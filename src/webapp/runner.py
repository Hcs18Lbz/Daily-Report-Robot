"""手动触发运行管理器: 单进程内单例, 用 threading.Lock 互斥。

并发边界:
- in-process 互斥: 同时只能有 1 个运行中, 第二次 trigger 立即抛 ConflictError。
- 跨进程 (例如计划任务起新进程): 锁无效, 安全靠 seen.json 去重; 这是已知边界。

状态文件:
- data/runs/<run_id>.json: 单次运行完整状态, 原子写 (tmp + os.replace)。
- data/run_history.json: 历史索引, 最多 50 条, 倒序, 原子写。

异常分支:
- run_pipeline 任何 unhandled exception 都会被捕获, 写 status="failed" + error=traceback,
  状态文件与 history 都得到终态, 前端永远能拿到一个明确的结束状态。
"""

import json
import logging
import os
import threading
import traceback
from datetime import datetime
from pathlib import Path

from src.main import run_pipeline

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).parent.parent.parent
_DATA_DIR = _PROJECT_ROOT / "data"
_RUNS_DIR = _DATA_DIR / "runs"
_HISTORY_PATH = _DATA_DIR / "run_history.json"
_HISTORY_MAX = 50


class ConflictError(Exception):
    """已有运行中, 拒绝新的 trigger。"""


class RunManager:
    """进程内单例, 加锁互斥, 状态落盘。"""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._runs: dict[str, dict] = {}
        self._active_run_id: str | None = None
        _RUNS_DIR.mkdir(parents=True, exist_ok=True)
        _ensure_history_file()

    def trigger(self, trigger: str = "manual") -> str:
        """启动一次运行 (后台线程)。成功返回 run_id; 已有运行中则 raise ConflictError。"""
        if not self._lock.acquire(blocking=False):
            raise ConflictError("上一次推送未结束")
        try:
            from src.models import RunResult
            from datetime import datetime as _dt
            started_at = _dt.now()
            run_id = f"{started_at.strftime('%Y%m%d')}-{os.urandom(4).hex()}"
            state: dict = {
                "run_id": run_id,
                "started_at": started_at.isoformat(timespec="seconds"),
                "finished_at": None,
                "status": "queued",
                "new_article_count": 0,
                "summary": "",
                "push_status": None,
                "error": None,
                "trigger": trigger,
            }
            self._runs[run_id] = state
            self._active_run_id = run_id
            _atomic_write_json(_run_path(run_id), state)
            thread = threading.Thread(target=self._execute, args=(run_id,), daemon=True)
            thread.start()
            logger.info("触发运行 %s (线程已启动)", run_id)
            return run_id
        except Exception:
            self._lock.release()
            self._active_run_id = None
            raise

    def _execute(self, run_id: str) -> None:
        """线程体: 跑 pipeline, 更新状态, 写 history, 释放锁。"""
        try:
            state = self._runs[run_id]
            state["status"] = "running"
            state["started_at"] = datetime.now().isoformat(timespec="seconds")
            _atomic_write_json(_run_path(run_id), state)

            result = run_pipeline(silent=True)

            state["finished_at"] = result.finished_at.isoformat(timespec="seconds")
            state["new_article_count"] = result.new_article_count
            state["summary"] = result.summary
            state["push_status"] = result.push_status
            state["error"] = result.error
            state["status"] = "success" if result.success else "failed"
        except Exception as e:
            tb = traceback.format_exc()
            logger.exception("运行 %s 异常: %s", run_id, e)
            state = self._runs.get(run_id, {})
            state["status"] = "failed"
            state["finished_at"] = datetime.now().isoformat(timespec="seconds")
            state["error"] = tb
        finally:
            _atomic_write_json(_run_path(run_id), state)
            _append_history(state)
            self._runs.pop(run_id, None)
            if self._active_run_id == run_id:
                self._active_run_id = None
            self._lock.release()
            logger.info("运行 %s 结束, status=%s", run_id, state.get("status"))

    def get_status(self, run_id: str) -> dict | None:
        """返回单次运行的当前状态 (内存优先, 缺失时回退到磁盘)。"""
        if run_id in self._runs:
            return dict(self._runs[run_id])
        path = _run_path(run_id)
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as e:
                logger.warning("读取运行状态失败 %s: %s", run_id, e)
        return None

    def list_history(self, limit: int = _HISTORY_MAX) -> list[dict]:
        """返回历史记录 (倒序, 最新在前), 最多 limit 条。"""
        if not _HISTORY_PATH.exists():
            return []
        try:
            data = json.loads(_HISTORY_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            logger.warning("读取 run_history.json 失败: %s", e)
            return []
        runs = data.get("runs", [])
        return list(runs[:limit])

    def get_run_detail(self, run_id: str) -> dict | None:
        """同 get_status, 语义上供历史详情使用。"""
        return self.get_status(run_id)


# ─── 内部工具 ──────────────────────────────────────────────────────────────────


def _run_path(run_id: str) -> Path:
    return _RUNS_DIR / f"{run_id}.json"


def _ensure_history_file() -> None:
    if not _HISTORY_PATH.exists():
        _atomic_write_json(_HISTORY_PATH, {"runs": []})


def _append_history(state: dict) -> None:
    """追加一条记录到 run_history.json, 倒序, 最多 _HISTORY_MAX 条。"""
    try:
        if _HISTORY_PATH.exists():
            data = json.loads(_HISTORY_PATH.read_text(encoding="utf-8"))
        else:
            data = {"runs": []}
    except (OSError, json.JSONDecodeError):
        data = {"runs": []}
    entry = {
        "run_id": state["run_id"],
        "started_at": state.get("started_at"),
        "finished_at": state.get("finished_at"),
        "status": state.get("status"),
        "new_article_count": state.get("new_article_count", 0),
        "push_status": state.get("push_status"),
        "trigger": state.get("trigger", "manual"),
    }
    data["runs"].insert(0, entry)
    data["runs"] = data["runs"][:_HISTORY_MAX]
    _atomic_write_json(_HISTORY_PATH, data)


def _atomic_write_json(path: Path, payload: dict) -> None:
    """写 JSON 到 path, tmp + os.replace 原子替换。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, path)
    except OSError:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass
        raise


# ─── 模块级单例 (放在所有依赖函数之后) ───────────────────────────────────────

manager = RunManager()
