import { create } from 'zustand';
import { Camera, CameraStatus } from '../types';

interface CameraState {
  cameras: Camera[];
  selectedCameraId: string | null;
  setCameras: (cameras: Camera[]) => void;
  updateCameraStatus: (cameraId: string, status: CameraStatus) => void;
  selectCamera: (cameraId: string | null) => void;
}

export const useCameraStore = create<CameraState>((set) => ({
  cameras: [],
  selectedCameraId: null,
  setCameras: (cameras) => set({ cameras }),
  updateCameraStatus: (cameraId, status) => set((state) => ({
    cameras: state.cameras.map((c) => 
      c.id === cameraId ? { ...c, status } : c
    )
  })),
  selectCamera: (cameraId) => set({ selectedCameraId: cameraId })
}));
export default useCameraStore;
