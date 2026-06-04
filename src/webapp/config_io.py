"""配置文件读写: RSS_FEEDS / .env / 调度时间。

设计原则:
- 读: 直接对文件 ast.parse, 不依赖 import 缓存, 改完立即可见。
- 写 config.py: 定位 RSS_FEEDS 值的字节区间, 仅替换该区间, 保留注释与排版。
  写前备份 config.py.bak, 写后 ast.parse 校验, 失败回滚。
- 写 .env: 用 python-dotenv 的 set_key (内部 tmp+rename, 原子写)。
- 写调度: 先 PowerShell 调 Register-ScheduledTask -Force, 成功才写 config.py 常量。
"""

import ast
import json
import logging
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from dotenv import dotenv_values, set_key

logger = logging.getLogger(__name__)

_CONFIG_PATH = Path(__file__).parent.parent / "config.py"
_CONFIG_BAK_PATH = _CONFIG_PATH.with_suffix(".py.bak")
_DOTENV_PATH = _CONFIG_PATH.parent.parent / ".env"
_TASKS = ("AI-News-Morning", "AI-News-Evening")
_SCHEDULE_KEYS = ("MORNING_SCHEDULE", "EVENING_SCHEDULE")
_TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
_RUN_BAT = _CONFIG_PATH.parent.parent / "run.bat"
_PROJECT_ROOT = _CONFIG_PATH.parent.parent


class ConfigIOError(Exception):
    pass


class ValidationError(ConfigIOError):
    pass


class ScheduleError(ConfigIOError):
    pass


# ─── 内部: config.py 字节级读写 ────────────────────────────────────────────────


def _to_byte_offset(source: str, lineno: int, col_offset: int) -> int:
    """ast 节点 (lineno, col_offset) -> 绝对字节偏移。"""
    lines = source.splitlines(keepends=True)
    offset = sum(len(lines[i].encode("utf-8")) for i in range(min(lineno - 1, len(lines))))
    return offset + col_offset


def _find_value_span(source: str, target_name: str) -> tuple[int, int]:
    """定位 `target_name = <value>` 中 <value> 的字节区间 (start, end)。"""
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == target_name:
            v = node.value
            return _to_byte_offset(source, v.lineno, v.col_offset), _to_byte_offset(source, v.end_lineno, v.end_col_offset)
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == target_name:
                    v = node.value
                    return _to_byte_offset(source, v.lineno, v.col_offset), _to_byte_offset(source, v.end_lineno, v.end_col_offset)
    raise ConfigIOError(f"config.py 中未找到 {target_name}")


def _splice_value(source: str, span: tuple[int, int], new_value_src: str) -> str:
    """将 source 中 [span[0]:span[1]] 区间替换为 new_value_src。"""
    b = source.encode("utf-8")
    return b[: span[0]].decode("utf-8") + new_value_src + b[span[1] :].decode("utf-8")


def _write_config_value(target_name: str, new_value_src: str) -> None:
    """备份 → 替换 → ast.parse 校验, 失败回滚。"""
    source = _CONFIG_PATH.read_text(encoding="utf-8")
    span = _find_value_span(source, target_name)
    new_source = _splice_value(source, span, new_value_src)
    shutil.copy2(_CONFIG_PATH, _CONFIG_BAK_PATH)
    try:
        _CONFIG_PATH.write_text(new_source, encoding="utf-8")
        ast.parse(new_source)
    except (SyntaxError, OSError) as e:
        shutil.copy2(_CONFIG_BAK_PATH, _CONFIG_PATH)
        raise ConfigIOError(f"config.py 写后校验失败, 已回滚: {e}") from e
    logger.info("config.py:%s 已更新", target_name)


# ─── RSS_FEEDS ────────────────────────────────────────────────────────────────


def read_rss_feeds() -> list[dict[str, str]]:
    """从 config.py 读 RSS_FEEDS 当前值 (不依赖 import 缓存)。"""
    source = _CONFIG_PATH.read_text(encoding="utf-8")
    span = _find_value_span(source, "RSS_FEEDS")
    raw = source.encode("utf-8")[span[0] : span[1]].decode("utf-8")
    value = ast.literal_eval(raw)
    if not isinstance(value, list) or not all(isinstance(x, dict) and "name" in x and "url" in x for x in value):
        raise ConfigIOError("RSS_FEEDS 数据格式异常")
    return [{"name": str(x["name"]), "url": str(x["url"])} for x in value]


def _validate_rss_feeds(feeds: list[dict[str, str]]) -> None:
    if not feeds:
        raise ValidationError("RSS 源列表不能为空")
    for i, f in enumerate(feeds):
        if not f.get("name", "").strip():
            raise ValidationError(f"第 {i + 1} 项: name 不能为空")
        url = f.get("url", "").strip()
        if not url:
            raise ValidationError(f"第 {i + 1} 项: url 不能为空")
        if not url.startswith(("http://", "https://")):
            raise ValidationError(f"第 {i + 1} 项: url 必须以 http:// 或 https:// 开头")


def write_rss_feeds(new_feeds: list[dict[str, str]]) -> None:
    """校验 → 备份 → 写 config.py:RSS_FEEDS → ast.parse 校验, 失败回滚。"""
    feeds = [{"name": f.get("name", "").strip(), "url": f.get("url", "").strip()} for f in new_feeds]
    _validate_rss_feeds(feeds)
    _write_config_value("RSS_FEEDS", repr(feeds))


# ─── .env ──────────────────────────────────────────────────────────────────────


def read_env(key: str) -> str:
    """从 .env 读 key 的当前值, 不存在返回 ''。"""
    values = dotenv_values(_DOTENV_PATH)
    return str(values.get(key, "") or "")


def write_env(key: str, value: str) -> None:
    """写 .env 中的一行 (python-dotenv 内部 tmp+rename, 原子写)。value 为空则视为清空。"""
    set_key(str(_DOTENV_PATH), key, value, quote_mode="always")
    logger.info(".env:%s 已更新", key)


# ─── 调度时间 (config.py 常量 + Task Scheduler) ────────────────────────────────


def read_schedule() -> dict[str, str]:
    """从 config.py 读 MORNING/EVENING_SCHEDULE。"""
    source = _CONFIG_PATH.read_text(encoding="utf-8")
    result: dict[str, str] = {}
    for key in _SCHEDULE_KEYS:
        span = _find_value_span(source, key)
        raw = source.encode("utf-8")[span[0] : span[1]].decode("utf-8")
        value = ast.literal_eval(raw)
        if not isinstance(value, str) or not _TIME_RE.match(value):
            raise ConfigIOError(f"{key} 格式异常: {value!r}")
        result[key.removesuffix("_SCHEDULE").lower()] = value
    return result


def _validate_time(t: str) -> None:
    if not _TIME_RE.match(t):
        raise ValidationError(f"时间格式错误: {t!r}, 应为 HH:MM (00:00~23:59)")


def _ps_register_tasks(morning: str, evening: str) -> None:
    """用 PowerShell Register-ScheduledTask 同步时间。失败抛 ScheduleError。"""
    ps = (
        f"$action = New-ScheduledTaskAction -Execute '{_RUN_BAT}' -WorkingDirectory '{_PROJECT_ROOT}'; "
        f"$tm = New-ScheduledTaskTrigger -Daily -At '{morning}'; "
        f"$te = New-ScheduledTaskTrigger -Daily -At '{evening}'; "
        f"$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable; "
        f"Register-ScheduledTask -TaskName 'AI-News-Morning' -Action $action -Trigger $tm -Settings $settings -Description 'Daily {morning} AI news push' -Force | Out-Null; "
        f"Register-ScheduledTask -TaskName 'AI-News-Evening' -Action $action -Trigger $te -Settings $settings -Description 'Daily {evening} AI news push' -Force | Out-Null"
    )
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
        raise ScheduleError(f"PowerShell 调用失败: {e}") from e
    if result.returncode != 0:
        raise ScheduleError(f"PowerShell 失败: {result.stderr.strip() or result.stdout.strip()}")


def write_schedule(morning: str, evening: str) -> None:
    """校验 → 同步到 Task Scheduler → 写 config.py。MORNING/EVENING_SCHEDULE 同步更新。"""
    _validate_time(morning)
    _validate_time(evening)
    _ps_register_tasks(morning, evening)
    _write_config_value("MORNING_SCHEDULE", repr(morning))
    _write_config_value("EVENING_SCHEDULE", repr(evening))


def get_next_run_times() -> dict[str, datetime | None]:
    """从 Task Scheduler 读 AI-News-Morning / AI-News-Evening 的 NextRunTime。任务不存在时为 None。"""
    script = (
        f"@{{"
        f"Morning = (Get-ScheduledTaskInfo -TaskName 'AI-News-Morning' -ErrorAction SilentlyContinue).NextRunTime; "
        f"Evening = (Get-ScheduledTaskInfo -TaskName 'AI-News-Evening' -ErrorAction SilentlyContinue).NextRunTime"
        f"}} | ConvertTo-Json"
    )
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
        logger.warning("读取 NextRunTime 失败: %s", e)
        return {"morning": None, "evening": None}
    if result.returncode != 0:
        logger.warning("PowerShell 读 NextRunTime 失败: %s", result.stderr.strip())
        return {"morning": None, "evening": None}
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        logger.warning("解析 NextRunTime JSON 失败: %s, raw=%r", e, result.stdout[:200])
        return {"morning": None, "evening": None}

    out: dict[str, datetime | None] = {}
    for label, key in (("morning", "Morning"), ("evening", "Evening")):
        raw = data.get(key)
        if not raw:
            out[label] = None
            continue
        try:
            out[label] = datetime.fromisoformat(str(raw).replace("Z", "+00:00")).replace(tzinfo=None)
        except (ValueError, TypeError) as e:
            logger.warning("解析 NextRunTime 失败 (%s): %s, raw=%r", label, e, raw)
            out[label] = None
    return out


def ensure_tasks() -> None:
    """webapp 启动时调用: 用 config.py 当前值注册/更新两个任务 (幂等)。失败仅记录。"""
    try:
        sched = read_schedule()
    except ConfigIOError as e:
        logger.warning("ensure_tasks: 读 schedule 失败: %s", e)
        return
    try:
        _ps_register_tasks(sched["morning"], sched["evening"])
        logger.info("ensure_tasks: 计划任务已同步到 %s / %s", sched["morning"], sched["evening"])
    except ScheduleError as e:
        logger.warning("ensure_tasks 失败: %s", e)
