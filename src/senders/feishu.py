"""飞书 Webhook 推送器。"""

import logging
from datetime import datetime

import requests

from src.senders.base import Sender

logger = logging.getLogger(__name__)


class FeishuSender(Sender):
    """通过飞书自定义机器人 Webhook 发送消息卡片。"""

    def __init__(self, webhook_url: str, silent: bool = False) -> None:
        self.webhook_url = webhook_url
        self.silent = silent

    def is_configured(self) -> bool:
        return bool(self.webhook_url) and "YOUR_WEBHOOK" not in self.webhook_url

    def send(self, payload: dict) -> bool:
        if not self.is_configured():
            logger.warning("未配置 FEISHU_WEBHOOK_URL，跳过推送")
            return False

        try:
            resp = requests.post(self.webhook_url, json=payload, timeout=10)
            resp.raise_for_status()
            result = resp.json()
            if result.get("code") == 0:
                logger.info("飞书推送成功")
                return True
            else:
                logger.error("飞书返回错误: %s", result)
                self._send_alert(f"飞书返回错误: {result}")
                return False
        except requests.RequestException as e:
            logger.error("飞书推送失败: %s", e)
            self._send_alert(f"飞书推送失败: {e}")
            return False

    def _send_alert(self, error_msg: str) -> None:
        """发送告警纯文本消息到同一群。silent=True 时不发告警 (webapp 手动触发场景)。"""
        if self.silent:
            return
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        alert = {
            "msg_type": "text",
            "content": {
                "text": f"⚠️ AI 新闻推送告警\n时间: {now}\n错误: {error_msg}\n请检查 scripts/run.bat 日志。",
            },
        }
        try:
            resp = requests.post(self.webhook_url, json=alert, timeout=10)
            if resp.status_code == 200:
                logger.info("告警消息已发送")
        except requests.RequestException as e:
            logger.error("告警消息发送失败: %s", e)
