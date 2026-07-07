import urllib.request
import urllib.parse
import json
from typing import Optional
from app.config import Settings
from app.core.logging import get_logger

logger = get_logger(__name__)

class NotificationService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.telegram_enabled = settings.notifications.telegram.enabled
        self.bot_token = settings.notifications.telegram.bot_token
        self.chat_id = settings.notifications.telegram.chat_id

    async def send_telegram(self, message: str, photo_bytes: Optional[bytes] = None) -> bool:
        if not self.telegram_enabled or not self.bot_token or not self.chat_id:
            logger.debug("Telegram notifications are disabled or missing settings")
            return False

        if photo_bytes:
            return await self._send_telegram_photo(message, photo_bytes)
        else:
            return await self._send_telegram_message(message)

    async def _send_telegram_message(self, message: str) -> bool:
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "HTML"
        }
        
        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=data,
                headers={"Content-Type": "application/json"}
            )
            # Run blocking HTTP call in thread executor to keep loop free
            import asyncio
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self._make_request, req)
            logger.info("Telegram message notification sent")
            return True
        except Exception as e:
            logger.error("Failed to send Telegram message notification", error=str(e))
            return False

    async def _send_telegram_photo(self, caption: str, photo_bytes: bytes) -> bool:
        url = f"https://api.telegram.org/bot{self.bot_token}/sendPhoto"
        
        # Build multipart form data manually to avoid external libraries
        boundary = "Boundary-EdgeAI-CCTV"
        
        body = []
        body.append(f"--{boundary}".encode("utf-8"))
        body.append(f'Content-Disposition: form-data; name="chat_id"'.encode("utf-8"))
        body.append("".encode("utf-8"))
        body.append(str(self.chat_id).encode("utf-8"))
        
        body.append(f"--{boundary}".encode("utf-8"))
        body.append(f'Content-Disposition: form-data; name="caption"'.encode("utf-8"))
        body.append("".encode("utf-8"))
        body.append(caption.encode("utf-8"))
        
        body.append(f"--{boundary}".encode("utf-8"))
        body.append(f'Content-Disposition: form-data; name="parse_mode"'.encode("utf-8"))
        body.append("".encode("utf-8"))
        body.append("HTML".encode("utf-8"))
        
        body.append(f"--{boundary}".encode("utf-8"))
        body.append(f'Content-Disposition: form-data; name="photo"; filename="alert.jpg"'.encode("utf-8"))
        body.append("Content-Type: image/jpeg".encode("utf-8"))
        body.append("".encode("utf-8"))
        body.append(photo_bytes)
        
        body.append(f"--{boundary}--".encode("utf-8"))
        body.append("".encode("utf-8"))
        
        data = b"\r\n".join(body)
        
        try:
            req = urllib.request.Request(
                url,
                data=data,
                headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}
            )
            import asyncio
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self._make_request, req)
            logger.info("Telegram photo notification sent")
            return True
        except Exception as e:
            logger.error("Failed to send Telegram photo notification", error=str(e))
            return False

    def _make_request(self, req: urllib.request.Request) -> None:
        with urllib.request.urlopen(req, timeout=10) as response:
            response.read()
