import smtplib
from email.mime.text import MIMEText
from typing import Dict, Any
import httpx

from app.config import Settings
from app.core.logging import get_logger

logger = get_logger(__name__)

class NotificationService:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def send_alert_notification(self, alert_data: Dict[str, Any]) -> None:
        """Send notifications across active configured channels."""
        # 1. Telegram channel
        if hasattr(self.settings, "notifications") and self.settings.notifications.telegram.enabled:
            await self._send_telegram(alert_data)
            
        # 2. Email SMTP channel
        if hasattr(self.settings, "notifications") and self.settings.notifications.email.enabled:
            await self._send_email(alert_data)

    async def _send_telegram(self, alert_data: Dict[str, Any]) -> None:
        token = self.settings.notifications.telegram.bot_token
        chat_id = self.settings.notifications.telegram.chat_id
        if not token or not chat_id:
            return
            
        msg = (
            f"⚠️ *SURVEILSENCE SECURITY ALERT* ⚠️\n"
            f"*Severity*: {alert_data.get('severity', '').upper()}\n"
            f"*Camera*: {alert_data.get('camera_id')}\n"
            f"*Zone*: {alert_data.get('zone_name') or 'N/A'}\n"
            f"*Description*: {alert_data.get('description')}\n"
            f"*Time*: {alert_data.get('timestamp')}"
        )
        
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        try:
            async with httpx.AsyncClient() as client:
                await client.post(url, json={
                    "chat_id": chat_id,
                    "text": msg,
                    "parse_mode": "Markdown"
                }, timeout=5.0)
            logger.info("Telegram alert notification sent successfully")
        except Exception as e:
            logger.error("Failed to send Telegram notification", error=str(e))

    async def _send_email(self, alert_data: Dict[str, Any]) -> None:
        # Sync SMTP execution inside executor to avoid blocking the event loop
        import asyncio
        loop = asyncio.get_running_loop()
        try:
            await loop.run_in_executor(None, self._send_email_sync, alert_data)
            logger.info("Email alert notification sent successfully")
        except Exception as e:
            logger.error("Failed to send Email notification", error=str(e))

    def _send_email_sync(self, alert_data: Dict[str, Any]) -> None:
        smtp_cfg = self.settings.notifications.email
        if not smtp_cfg.smtp_host:
            return
            
        msg = MIMEText(
            f"SURVEILSENCE SECURITY ALERT\n\n"
            f"Severity: {alert_data.get('severity', '').upper()}\n"
            f"Camera: {alert_data.get('camera_id')}\n"
            f"Zone: {alert_data.get('zone_name') or 'N/A'}\n"
            f"Description: {alert_data.get('description')}\n"
            f"Time: {alert_data.get('timestamp')}"
        )
        msg['Subject'] = f"SURVEILSENCE ALERT - {alert_data.get('severity', '').upper()}"
        msg['From'] = "alerts@surveilsence.local"
        msg['To'] = "admin@surveilsence.local"
        
        with smtplib.SMTP(smtp_cfg.smtp_host, smtp_cfg.smtp_port) as server:
            server.send_message(msg)
