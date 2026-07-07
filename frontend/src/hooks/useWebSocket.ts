import { useEffect, useState } from 'react';
import wsService from '../services/websocket';
import useCameraStore from '../store/cameraStore';
import useAlertStore from '../store/alertStore';

export function useWebSocket() {
  const [connected, setConnected] = useState<boolean>(false);
  const updateCameraStatus = useCameraStore((state) => state.updateCameraStatus);
  const addAlert = useAlertStore((state) => state.addAlert);

  useEffect(() => {
    // 1. Connect
    wsService.connect();
    
    // 2. Subscribe to status events
    const unsubOpen = wsService.subscribe('open', () => setConnected(true));
    const unsubClose = wsService.subscribe('close', () => setConnected(false));
    
    // Status update mapping from camera events
    const unsubStatus = wsService.subscribe('camera_status', (msg: any) => {
      if (msg.camera_id && msg.status) {
        updateCameraStatus(msg.camera_id, msg.status);
      }
    });

    const unsubAlert = wsService.subscribe('alert', (msg: any) => {
      if (msg.data) {
        addAlert(msg.data);
      }
    });

    return () => {
      unsubOpen();
      unsubClose();
      unsubStatus();
      unsubAlert();
    };
  }, [updateCameraStatus, addAlert]);

  return { connected };
}
export default useWebSocket;
