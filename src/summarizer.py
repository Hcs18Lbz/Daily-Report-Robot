"""AI 摘要模块 — 调用 NVIDIA NIM API。"""

import logging

import requests

from src.models import Article
from src.config import LLM_MODEL, NVIDIA_API_KEY

logger = logging.getLogger(__name__)

API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"


def summarize(articles: list[Article]) -> str:
    """调用 LLM 生成带引用标注的中文摘要。"""
    if not articles:
        return "今日暂无新内容。"

    if not NVIDIA_API_KEY:
        logger.warning("未配置 NVIDIA_API_KEY，跳过 AI 摘要")
        return "⚠️ 未配置 API Key，仅展示原始新闻。"

    prompt = _build_prompt(articles)
    logger.info("正在调用 NVIDIA NIM API 生成摘要...")

    try:
        resp = requests.post(
            API_URL,
            headers={
                "Authorization": f"Bearer {NVIDIA_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": LLM_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 800,
            },
            timeout=60,
        )
        resp.raise_for_status()
        result = resp.json()
        summary = result["choices"][0]["message"]["content"]
        logger.info("摘要生成成功")
        return summary

    except requests.RequestException as e:
        logger.error("LLM 调用失败: %s", e)
        return "⚠️ 摘要生成失败，请稍后重试。"


def _build_prompt(articles: list[Article]) -> str:
    """构建 LLM prompt，要求生成新闻简报风格输出。"""
    news_items = []
    for i, a in enumerate(articles, 1):
        desc = a.description.strip()
        news_items.append(f"[{i}] [{a.source}] {a.title}\n    {desc}")

    return (
        "你是一名资深 AI 行业资讯编辑。请根据以下新闻条目，生成一份**新闻简报**。\n\n"
        "输出格式要求（严格遵守）：\n\n"
        "1. 第一行写一句总览摘要，以 **\u3010核心资讯汇总\u3011** 开头，概括今日 AI 领域焦点\n"
        "2. 将新闻按主题分为 3-5 个板块，每个板块用 **一、板块标题（4-6字）** 格式\n"
        "3. 每个板块下列出 1-3 条新闻，编号从 1 开始，格式为：**新闻标题**：详细内容（50-100字），包含关键数据、定价、时间等具体信息\n"
        "4. 最后写一个 **\u3010延伸阅读\u3011** 板块，列出所有新闻的序号和链接\n\n"
        "示例格式：\n"
        "\u3010核心资讯汇总\u3011今日AI领域聚焦...\n"
        "一、巨头模型对决\n"
        "1. **微软发布MAI系列**：MAI-Transcribe-1词错误率3.9%...\n"
        "2. **谷歌发布Gemma 4**：31B模型列开放模型全球第3位...\n"
        "二、AI编程生态\n"
        "1. **Claw Code开源**：3天GitHub Stars破7.2万...\n"
        "\u3010延伸阅读\u3011\n"
        "[1] 标题 → 链接\n"
        "[2] 标题 → 链接\n\n"
        "要求：\n"
        "- 用简洁专业的中文\n"
        "- 保留关键数据（数字、价格、百分比）\n"
        "- 忽略重复或低价值内容\n"
        "- 总字数控制在 500 字以内\n\n"
        "新闻内容：\n" + "\n\n".join(news_items)
    )
