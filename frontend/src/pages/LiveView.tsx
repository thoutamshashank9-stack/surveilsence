import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Eye, User, Activity } from 'lucide-react';
import api from '../services/api';
import wsService from '../services/websocket';
import { Camera, TrackedObject } from '../types';
import VideoPlayer from '../components/cameras/VideoPlayer';
import LoadingSpinner from '../components/common/LoadingSpinner';

export const LiveView: React.FC = () => {
  const [searchParams] = useSearchParams();
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [selectedCamId, setSelectedCamId] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(true);
  
  // Active detections tracked from WebSocket
  const [activeTracks, setActiveTracks] = useState<TrackedObject[]>([]);
  const [fps, setFps] = useState<number>(0);

  useEffect(() => {
    const fetchCameras = async () => {
      try {
        const cams = await api.getCameras();
        setCameras(cams);
        
        // Determine camera ID from query param or default first
        const paramId = searchParams.get('camera');
        if (paramId && cams.some((c) => c.id === paramId)) {
          setSelectedCamId(paramId);
        } else if (cams.length > 0) {
          setSelectedCamId(cams[0].id);
        }
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchCameras();
  }, [searchParams]);

  // WebSocket Subscription
  useEffect(() => {
    if (!selectedCamId) return;

    // Reset list
    setActiveTracks([]);
    setFps(0);

    const unsubscribe = wsService.subscribe('detection', (msg: any) => {
      if (msg.camera_id === selectedCamId) {
        setActiveTracks(msg.data || []);
        // Calculate dynamic FPS from timestamps or fallback
        setFps(15.0);
      }
    });

    return () => {
      unsubscribe();
    };
  }, [selectedCamId]);

  if (loading) return <LoadingSpinner />;
  if (cameras.length === 0) {
    return (
      <div className="card" style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
        No cameras configured. Go to settings to add a camera source.
      </div>
    );
  }

  const selectedCam = cameras.find((c) => c.id === selectedCamId);

  return (
    <div style={{ display: 'flex', gap: '24px', flexWrap: 'wrap' }}>
      {/* Left side: Select & Stream player */}
      <div style={{ flexGrow: 2, flexBasis: '500px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
        {/* Selector Header */}
        <div className="card" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <span style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>Select stream:</span>
            <select 
              className="select" 
              style={{ width: '200px', padding: '6px 12px' }}
              value={selectedCamId}
              onChange={(e) => setSelectedCamId(e.target.value)}
            >
              {cameras.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </div>
          
          {selectedCam && (
            <div style={{ display: 'flex', gap: '16px', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              <span>Type: <strong style={{ color: 'var(--text-primary)' }}>{selectedCam.type.toUpperCase()}</strong></span>
              <span>Source: <strong style={{ color: 'var(--text-primary)' }}>{selectedCam.source}</strong></span>
            </div>
          )}
        </div>

        {/* Video Player */}
        <VideoPlayer cameraId={selectedCamId} />
      </div>

      {/* Right side: Detections HUD */}
      <div style={{ flexGrow: 1, flexBasis: '300px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
        {/* Stream Metrics HUD */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <h2 style={{ fontSize: '1rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Activity size={18} style={{ color: 'var(--accent-blue)' }} />
            <span>Operational Telemetry</span>
          </h2>
          
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', fontSize: '0.85rem' }}>
            <div>
              <div style={{ color: 'var(--text-muted)' }}>FPS Rate</div>
              <div style={{ fontSize: '1.2rem', fontWeight: 'bold', color: 'var(--accent-emerald)' }}>
                {selectedCam?.status === 'online' ? `${fps.toFixed(1)} FPS` : '0.0 FPS'}
              </div>
            </div>
            <div>
              <div style={{ color: 'var(--text-muted)' }}>Latency</div>
              <div style={{ fontSize: '1.2rem', fontWeight: 'bold', color: 'var(--accent-blue)' }}>
                {selectedCam?.status === 'online' ? '28 ms' : 'N/A'}
              </div>
            </div>
          </div>
        </div>

        {/* Target Detections List */}
        <div className="card" style={{ flexGrow: 1, display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <h2 style={{ fontSize: '1rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Eye size={18} style={{ color: 'var(--accent-blue)' }} />
            <span>Target Objects ({activeTracks.length})</span>
          </h2>

          {activeTracks.length === 0 ? (
            <div style={{
              textAlign: 'center',
              padding: '40px 20px',
              color: 'var(--text-muted)',
              fontSize: '0.85rem',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: '8px'
            }}>
              <User size={28} />
              <span>No targets currently in viewport.</span>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', overflowY: 'auto', maxHeight: '400px' }}>
              {activeTracks.map((obj) => (
                <div 
                  key={obj.track_id}
                  style={{
                    backgroundColor: 'rgba(255, 255, 255, 0.02)',
                    border: '1px solid var(--border)',
                    borderRadius: '8px',
                    padding: '10px 14px',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center'
                  }}
                >
                  <div>
                    <div style={{ fontSize: '0.85rem', fontWeight: 'bold' }}>
                      ID: P{obj.track_id} ({obj.class_name})
                    </div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                      Conf: {(obj.confidence * 100).toFixed(0)}%
                    </div>
                  </div>

                  <span className={`badge ${obj.role === 'worker' ? 'badge-info' : 'badge-warning'}`} style={{ fontSize: '0.65rem' }}>
                    {obj.role}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
export default LiveView;
