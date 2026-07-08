import { Camera, Alert, FootfallMetrics, DwellMetrics, HeatmapData, SystemStatus, HardwareInfo } from '../types';

const API_BASE = '/api/v1';
const DEV_TOKEN = 'dev-secret-key-12345';

const getHeaders = () => {
  return {
    'Content-Type': 'application/json',
    'X-API-Key': DEV_TOKEN
  };
};

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const errorText = await response.text();
    let errorMessage = `API Error: ${response.status} ${response.statusText}`;
    try {
      const errorJson = JSON.parse(errorText);
      errorMessage = errorJson.detail || errorMessage;
    } catch {
      // Ignored
    }
    throw new Error(errorMessage);
  }
  return response.json() as Promise<T>;
}

export const api = {
  async getHealth(): Promise<SystemStatus> {
    const res = await fetch(`${API_BASE}/system/health`);
    return handleResponse<SystemStatus>(res);
  },

  async getHardware(): Promise<HardwareInfo> {
    const res = await fetch(`${API_BASE}/system/hardware`, { headers: getHeaders() });
    return handleResponse<HardwareInfo>(res);
  },

  async getCameras(): Promise<Camera[]> {
    const res = await fetch(`${API_BASE}/cameras`, { headers: getHeaders() });
    return handleResponse<Camera[]>(res);
  },

  async getCamera(id: string): Promise<Camera> {
    const res = await fetch(`${API_BASE}/cameras/${id}`, { headers: getHeaders() });
    return handleResponse<Camera>(res);
  },

  async createCamera(camera: any): Promise<Camera> {
    const res = await fetch(`${API_BASE}/cameras`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify(camera)
    });
    return handleResponse<Camera>(res);
  },

  async deleteCamera(id: string): Promise<void> {
    const res = await fetch(`${API_BASE}/cameras/${id}`, {
      method: 'DELETE',
      headers: getHeaders()
    });
    if (!res.ok) {
      throw new Error(`Failed to delete camera: ${res.statusText}`);
    }
  },

  async getAlerts(filters: {
    camera_id?: string;
    severity?: string;
    status?: string;
    start_date?: string;
    end_date?: string;
    limit?: number;
    offset?: number;
  } = {}): Promise<Alert[]> {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([key, val]) => {
      if (val !== undefined && val !== null && val !== '') {
        params.append(key, String(val));
      }
    });
    const res = await fetch(`${API_BASE}/alerts?${params.toString()}`, { headers: getHeaders() });
    return handleResponse<Alert[]>(res);
  },

  async acknowledgeAlert(id: number, acknowledged_by: string, notes?: string): Promise<Alert> {
    const res = await fetch(`${API_BASE}/alerts/${id}/acknowledge`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({ acknowledged_by, notes })
    });
    return handleResponse<Alert>(res);
  },

  async explainAlertVLM(id: number): Promise<Alert> {
    const res = await fetch(`${API_BASE}/alerts/${id}/vlm-explain`, {
      method: 'POST',
      headers: getHeaders()
    });
    return handleResponse<Alert>(res);
  },

  async getAlertStats(): Promise<any> {
    const res = await fetch(`${API_BASE}/alerts/stats`, { headers: getHeaders() });
    return handleResponse<any>(res);
  },

  async getFootfall(cameraId: string, dateStr?: string): Promise<FootfallMetrics> {
    const params = new URLSearchParams({ camera_id: cameraId });
    if (dateStr) params.append('date', dateStr);
    const res = await fetch(`${API_BASE}/analytics/footfall?${params.toString()}`, { headers: getHeaders() });
    return handleResponse<FootfallMetrics>(res);
  },

  async getDwellStats(cameraId: string, dateStr?: string): Promise<DwellMetrics> {
    const params = new URLSearchParams({ camera_id: cameraId });
    if (dateStr) params.append('date', dateStr);
    const res = await fetch(`${API_BASE}/analytics/dwell?${params.toString()}`, { headers: getHeaders() });
    return handleResponse<DwellMetrics>(res);
  },

  async getHeatmap(cameraId: string, hoursAgo: number = 24): Promise<HeatmapData> {
    const params = new URLSearchParams({ camera_id: cameraId, hours_ago: String(hoursAgo) });
    const res = await fetch(`${API_BASE}/analytics/heatmap?${params.toString()}`, { headers: getHeaders() });
    return handleResponse<HeatmapData>(res);
  }
};
export default api;
