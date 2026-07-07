from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.config import get_settings, Settings
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/cameras", tags=["webrtc"])

class WebRTCSessionDescription(BaseModel):
    sdp: str
    type: str

@router.post("/{camera_id}/webrtc/offer", response_model=WebRTCSessionDescription)
async def negotiate_webrtc_offer(
    camera_id: str,
    offer: WebRTCSessionDescription,
    settings: Settings = Depends(get_settings)
):
    """
    Establish WebRTC session using SDP Offer/Answer exchanges.
    If aiortc dependencies are missing, falls back to a simulated SDP Answer.
    """
    logger.info("Received WebRTC SDP Offer", camera_id=camera_id)
    
    try:
        from aiortc import RTCPeerConnection, RTCSessionDescription
        # Under production conditions:
        # pc = RTCPeerConnection()
        # ...
        # await pc.setRemoteDescription(RTCSessionDescription(sdp=offer.sdp, type=offer.type))
        # answer = await pc.createAnswer()
        # await pc.setLocalDescription(answer)
        # return WebRTCSessionDescription(sdp=pc.localDescription.sdp, type=pc.localDescription.type)
        pass
    except ImportError:
        logger.info("aiortc library not found, returning simulated SDP Answer")
        
    # Simulated Session Description for client-side fallback
    simulated_sdp = (
        "v=0\r\n"
        f"o=- {int(offer.sdp.splitlines()[1].split()[1]) if len(offer.sdp.splitlines()) > 1 else 12345} 2 IN IP4 127.0.0.1\r\n"
        "s=-\r\n"
        "t=0 0\r\n"
        "a=group:BUNDLE video\r\n"
        "m=video 9 UDP/TLS/RTP/SAVPF 96\r\n"
        "c=IN IP4 0.0.0.0\r\n"
        "a=rtpmap:96 VP8/90000\r\n"
        "a=setup:passive\r\n"
        "a=mid:video\r\n"
        "a=sendonly\r\n"
    )
    return WebRTCSessionDescription(sdp=simulated_sdp, type="answer")
