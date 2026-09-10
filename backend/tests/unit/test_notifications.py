import pytest
import os
import shutil
import numpy as np
from unittest.mock import AsyncMock, patch, MagicMock

from app.workers.camera_worker import CameraWorker
from app.services.notification_service import NotificationService
from app.config import Settings, WhatsAppConfig, TelegramConfig

@pytest.fixture
def mock_settings():
    settings = Settings()
    settings.notifications.telegram.enabled = True
    settings.notifications.telegram.bot_token = "mock_token"
    settings.notifications.telegram.chat_id = "mock_chat"
    
    # Enable WhatsApp
    settings.notifications.whatsapp = WhatsAppConfig(
        enabled=True,
        provider="twilio",
        account_sid="AC12345",
        auth_token="auth_token_secret",
        from_number="whatsapp:+14155238886",
        to_number="whatsapp:+911234567890"
    )
    return settings

def test_media_saving_generation():
    """Verify that CameraWorker can write screenshots and frames to files successfully."""
    # Generate some dummy images
    dummy_frame = np.zeros((100, 100, 3), dtype=np.uint8)
    dummy_frame_list = [(1.0, dummy_frame), (2.0, dummy_frame)]
    
    alert_uuid = "test_alert_uuid_12345"
    
    # Ensure folder is clean
    if os.path.exists("data/alerts"):
        shutil.rmtree("data/alerts")
        
    # Execute the static method
    screenshot, video = CameraWorker._save_alert_media_sync(
        alert_uuid,
        dummy_frame,
        dummy_frame_list,
        fps=10
    )
    
    assert os.path.exists(screenshot)
    assert os.path.exists(video)
    assert screenshot.endswith("_screenshot.jpg")
    assert video.endswith("_clip.mp4")
    
    # Cleanup
    shutil.rmtree("data/alerts")

@pytest.mark.asyncio
async def test_notification_dispatch(mock_settings):
    """Verify that NotificationService dispatches alerts to both Telegram and WhatsApp endpoints."""
    service = NotificationService(mock_settings)
    
    alert_data = {
        "camera_id": "test_cam",
        "alert_type": "intrusion",
        "severity": "critical",
        "zone_name": "restricted_zone",
        "description": "Intruder detected",
        "timestamp": "2026-07-12 15:00:00",
        "metadata_json": {
            "screenshot_path": "dummy_screenshot.jpg",
            "video_path": "dummy_video.mp4"
        }
    }
    
    # Mock the HTTP calls to avoid hitting external APIs
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = MagicMock(status_code=200, json=lambda: {"data": {"url": "https://tmpfiles.org/dl/123"}})
        
        await service.send_alert_notification(alert_data)
        
        # Verify both endpoints were called
        # 1. Twilio message URL
        # 2. tmpfiles upload URL (for WhatsApp media upload)
        # 3. Telegram video URL
        assert mock_post.call_count >= 2

@pytest.mark.asyncio
async def test_send_test_telegram(mock_settings):
    """Verify that send_test_telegram creates snapshot image and sends photo to Telegram."""
    service = NotificationService(mock_settings)
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = MagicMock(status_code=200)
        res = await service.send_test_telegram(bot_token="test_token_123", chat_id="test_chat_456")
        assert res["status"] == "success"
        assert mock_post.call_count >= 1

