from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from app.config import get_settings, Settings
from app.core.logging import get_logger
from app.api.deps import get_camera_manager
from app.services.camera_manager import CameraManager
from app.models.enums import CameraStatus
import asyncio
import cv2
import numpy as np

logger = get_logger(__name__)

router = APIRouter(prefix="/cameras", tags=["webrtc"])

class WebRTCSessionDescription(BaseModel):
    sdp: str
    type: str

try:
    from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
    from av import VideoFrame
    
    class CameraVideoTrack(VideoStreamTrack):
        kind = "video"
        
        def __init__(self, camera_manager: CameraManager, camera_id: str):
            super().__init__()
            self.camera_manager = camera_manager
            self.camera_id = camera_id
            
        async def recv(self):
            # Limit frame rate to camera cap
            pts, time_base = await self.next_timestamp()
            
            # Read frame from camera manager
            ret, frame = self.camera_manager.get_frame(self.camera_id)
            if not ret or frame is None:
                # Fallback: create a dummy black frame
                frame = np.zeros((480, 640, 3), dtype=np.uint8)
                cv2.putText(
                    frame, 
                    "Camera offline / Frame buffer empty", 
                    (50, 240), 
                    cv2.FONT_HERSHEY_SIMPLEX, 
                    0.6, 
                    (0, 0, 255), 
                    2
                )
            
            # Convert BGR (OpenCV) to RGB (PyAV / WebRTC expects RGB)
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Create av.VideoFrame
            new_frame = VideoFrame.from_ndarray(frame_rgb, format="rgb24")
            new_frame.pts = pts
            new_frame.time_base = time_base
            return new_frame

except ImportError:
    CameraVideoTrack = None


@router.post("/{camera_id}/webrtc/offer", response_model=WebRTCSessionDescription)
async def negotiate_webrtc_offer(
    camera_id: str,
    offer: WebRTCSessionDescription,
    request: Request,
    settings: Settings = Depends(get_settings),
    camera_manager: CameraManager = Depends(get_camera_manager)
):
    """
    Establish WebRTC session using SDP Offer/Answer exchanges.
    If aiortc dependencies are missing, falls back to a simulated SDP Answer.
    """
    logger.info("Received WebRTC SDP Offer", camera_id=camera_id)
    
    if CameraVideoTrack is not None:
        try:
            from aiortc import RTCPeerConnection, RTCSessionDescription
            
            pc = RTCPeerConnection()
            
            # Keep tracks/connections registered on app state to cleanly dispose on shutdown
            if not hasattr(request.app.state, "peer_connections"):
                request.app.state.peer_connections = []
            request.app.state.peer_connections.append(pc)
            
            # Create camera video track
            video_track = CameraVideoTrack(camera_manager, camera_id)
            pc.addTrack(video_track)
            
            # Handle state transitions
            @pc.on("iceconnectionstatechange")
            async def on_iceconnectionstatechange():
                logger.info("ICE connection state changed", state=pc.iceConnectionState, camera_id=camera_id)
                if pc.iceConnectionState in ["failed", "closed"]:
                    await pc.close()
                    if pc in request.app.state.peer_connections:
                        request.app.state.peer_connections.remove(pc)
            
            # Set remote description (SDP Offer)
            await pc.setRemoteDescription(RTCSessionDescription(sdp=offer.sdp, type=offer.type))
            
            # Create local description (SDP Answer)
            answer = await pc.createAnswer()
            await pc.setLocalDescription(answer)
            
            return WebRTCSessionDescription(
                sdp=pc.localDescription.sdp,
                type=pc.localDescription.type
            )
            
        except Exception as ex:
            logger.error("WebRTC session negotiation failed, falling back to simulated answer", error=str(ex))
            
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

