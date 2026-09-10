import smtplib
import os
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
        # Normalize dict representation (SQLAlchemy models mapped to dictionary keys)
        data = alert_data
        if hasattr(alert_data, "__table__"):
            # It's an ORM object, extract dict representation
            meta = alert_data.metadata_json or {}
            data = {
                "camera_id": alert_data.camera_id,
                "alert_type": alert_data.alert_type,
                "severity": alert_data.severity,
                "zone_name": alert_data.zone_name,
                "description": alert_data.description,
                "timestamp": str(alert_data.timestamp),
                "metadata_json": meta if isinstance(meta, dict) else {}
            }

        # 1. Telegram channel
        if hasattr(self.settings, "notifications") and self.settings.notifications.telegram.enabled:
            await self._send_telegram(data)
            
        # 2. WhatsApp channel
        if hasattr(self.settings, "notifications") and self.settings.notifications.whatsapp.enabled:
            await self._send_whatsapp(data)

        # 3. Email SMTP channel
        if hasattr(self.settings, "notifications") and self.settings.notifications.email.enabled:
            await self._send_email(data)

    async def send_test_telegram(self, bot_token: Optional[str] = None, chat_id: Optional[str] = None) -> Dict[str, Any]:
        """Generate a test warning image and send it to the Telegram bot."""
        import cv2
        import numpy as np
        import time

        token = bot_token or getattr(self.settings.notifications.telegram, "bot_token", "")
        cid = chat_id or getattr(self.settings.notifications.telegram, "chat_id", "")
        if not token or not cid:
            raise ValueError("Telegram bot_token and chat_id are required")

        # Generate test warning image
        img = np.zeros((480, 640, 3), dtype=np.uint8)
        img[:] = (30, 30, 30)
        # Grid lines
        for x in range(0, 640, 50):
            cv2.line(img, (x, 0), (x, 480), (45, 45, 45), 1)
        for y in range(0, 480, 50):
            cv2.line(img, (0, y), (640, y), (45, 45, 45), 1)

        cv2.putText(img, "SURVEILSENCE SECURITY ALERT", (40, 180), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
        cv2.putText(img, "WARNING: TEST SECURITY EVENT DETECTED", (40, 230), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 165, 255), 2)
        cv2.putText(img, f"TIMESTAMP: {time.strftime('%Y-%m-%d %H:%M:%S')}", (40, 280), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1)
        cv2.rectangle(img, (200, 120), (440, 320), (0, 0, 255), 2)

        os.makedirs("data", exist_ok=True)
        test_img_path = "data/telegram_test_warning.jpg"
        cv2.imwrite(test_img_path, img)

        alert_data = {
            "camera_id": "TEST_CAM_01",
            "alert_type": "test_warning",
            "severity": "critical",
            "zone_name": "Main Entrance",
            "description": "TEST SECURITY ALERT: Rule-based unusual activity test warning with snapshot image.",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "metadata_json": {"screenshot_path": test_img_path}
        }

        # Override temporary token/chat_id if custom parameters provided
        orig_token = self.settings.notifications.telegram.bot_token
        orig_chat = self.settings.notifications.telegram.chat_id
        try:
            self.settings.notifications.telegram.bot_token = token
            self.settings.notifications.telegram.chat_id = cid
            await self._send_telegram(alert_data)
            return {"status": "success", "message": "Test warning image sent to Telegram bot successfully!"}
        finally:
            self.settings.notifications.telegram.bot_token = orig_token
            self.settings.notifications.telegram.chat_id = orig_chat

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
        
        meta = alert_data.get("metadata_json", {})
        screenshot_path = meta.get("screenshot_path")
        video_path = meta.get("video_path")
        
        async with httpx.AsyncClient() as client:
            try:
                # 1. Send Video Clip if available
                if video_path and os.path.exists(video_path):
                    url = f"https://api.telegram.org/bot{token}/sendVideo"
                    with open(video_path, "rb") as video_file:
                        files = {"video": video_file}
                        data = {"chat_id": chat_id, "caption": msg, "parse_mode": "Markdown"}
                        r = await client.post(url, data=data, files=files, timeout=30.0)
                    if r.status_code == 200:
                        logger.info("Telegram alert video clip sent successfully")
                        return
                    else:
                        logger.error("Failed to send video via Telegram, attempting fallback", response=r.text)

                # 2. Send Photo Screenshot if available
                if screenshot_path and os.path.exists(screenshot_path):
                    url = f"https://api.telegram.org/bot{token}/sendPhoto"
                    with open(screenshot_path, "rb") as photo_file:
                        files = {"photo": photo_file}
                        data = {"chat_id": chat_id, "caption": msg, "parse_mode": "Markdown"}
                        r = await client.post(url, data=data, files=files, timeout=15.0)
                    if r.status_code == 200:
                        logger.info("Telegram alert screenshot sent successfully")
                        return
                    else:
                        logger.error("Failed to send photo via Telegram, attempting fallback", response=r.text)

                # 3. Fallback to Text Message
                url = f"https://api.telegram.org/bot{token}/sendMessage"
                await client.post(url, json={
                    "chat_id": chat_id,
                    "text": msg,
                    "parse_mode": "Markdown"
                }, timeout=5.0)
                logger.info("Telegram alert text notification sent successfully")
            except Exception as e:
                logger.error("Failed to send Telegram notification", error=str(e))

    async def _send_whatsapp(self, alert_data: Dict[str, Any]) -> None:
        ws_cfg = self.settings.notifications.whatsapp
        if not ws_cfg.account_sid or not ws_cfg.auth_token:
            return
            
        msg = (
            f"⚠️ *SURVEILSENCE SECURITY ALERT* ⚠️\n"
            f"Severity: {alert_data.get('severity', '').upper()}\n"
            f"Camera: {alert_data.get('camera_id')}\n"
            f"Zone: {alert_data.get('zone_name') or 'N/A'}\n"
            f"Description: {alert_data.get('description')}\n"
            f"Time: {alert_data.get('timestamp')}"
        )
        
        meta = alert_data.get("metadata_json", {})
        screenshot_path = meta.get("screenshot_path")
        
        media_url = None
        
        # Twilio WhatsApp requires a public URL. Upload to free host if screenshot is present.
        if screenshot_path and os.path.exists(screenshot_path):
            try:
                async with httpx.AsyncClient() as client:
                    with open(screenshot_path, "rb") as f:
                        files = {"file": f}
                        r = await client.post("https://tmpfiles.org/api/v1/upload", files=files, timeout=15.0)
                    if r.status_code == 200:
                        view_url = r.json().get("data", {}).get("url")
                        if view_url:
                            # Convert view URL to direct download link
                            media_url = view_url.replace("https://tmpfiles.org/", "https://tmpfiles.org/dl/")
                            logger.info("Uploaded screenshot to temp host for WhatsApp Twilio media", media_url=media_url)
            except Exception as e:
                logger.error("Failed to upload WhatsApp screenshot to temp host", error=str(e))

        url = f"https://api.twilio.com/2010-04-01/Accounts/{ws_cfg.account_sid}/Messages.json"
        auth = (ws_cfg.account_sid, ws_cfg.auth_token)
        
        # Ensure To and From are prefixed correctly for Twilio WhatsApp
        to_number = ws_cfg.to_number if ws_cfg.to_number.startswith("whatsapp:") else f"whatsapp:{ws_cfg.to_number}"
        from_number = ws_cfg.from_number if ws_cfg.from_number.startswith("whatsapp:") else f"whatsapp:{ws_cfg.from_number}"
        
        data = {
            "From": from_number,
            "To": to_number,
            "Body": msg
        }
        if media_url:
            data["MediaUrl"] = media_url
            
        try:
            async with httpx.AsyncClient() as client:
                r = await client.post(url, data=data, auth=auth, timeout=10.0)
            if r.status_code in [200, 201]:
                logger.info("WhatsApp Twilio alert notification sent successfully")
            else:
                logger.error("Failed to send WhatsApp Twilio message", status=r.status_code, response=r.text)
        except Exception as e:
            logger.error("Failed to send WhatsApp Twilio notification", error=str(e))

    async def _send_email(self, alert_data: Dict[str, Any]) -> None:
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
