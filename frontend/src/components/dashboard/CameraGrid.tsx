import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Camera as CameraIcon, PlayCircle } from 'lucide-react';
import { Camera } from '../../types';

interface CameraGridProps {
  cameras: Camera[];
}

export const CameraGrid: React.FC<CameraGridProps> = ({ cameras }) => {
  const navigate = useNavigate();

  if (cameras.length === 0) {
    return (
      <div 
        className="card fade-in"
        style={{
          marginTop: '20px',
          padding: '48px 24px',
          textAlign: 'center',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '16px',
          border: '1px dashed var(--border)',
          backgroundColor: 'rgba(255, 255, 255, 0.02)'
        }}
      >
        <div style={{
          width: '56px',
          height: '56px',
          borderRadius: '50%',
          backgroundColor: 'rgba(59, 130, 246, 0.1)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'var(--accent-blue)'
        }}>
          <CameraIcon size={28} />
        </div>
        <div>
          <h3 style={{ fontSize: '1.05rem', fontWeight: 600, marginBottom: '6px' }}>No Camera Streams Connected</h3>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', maxWidth: '420px', margin: '0 auto' }}>
            Connect a real camera stream (such as a mobile phone IP webcam or RTSP IP camera) in Settings to begin live surveillance and behavioral analytics.
          </p>
        </div>
        <button 
          className="btn btn-primary"
          style={{ marginTop: '8px', padding: '8px 20px', fontSize: '0.85rem' }}
          onClick={() => navigate('/settings')}
        >
          Add Camera Feed
        </button>
      </div>
    );
  }

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
      gap: '20px',
      marginTop: '20px'
    }}>
      {cameras.map((camera) => (
        <div 
          key={camera.id}
          className="card fade-in"
          style={{ cursor: 'pointer', padding: '16px' }}
          onClick={() => navigate(`/live?camera=${camera.id}`)}
        >
          {/* Header */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <h3 style={{ fontSize: '0.95rem', fontWeight: 600 }}>{camera.name}</h3>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span className={`status-dot ${camera.status === 'online' ? 'online' : 'offline'}`}></span>
              <span style={{ fontSize: '0.75rem', textTransform: 'capitalize', color: 'var(--text-secondary)' }}>
                {camera.status}
              </span>
            </div>
          </div>

          {/* Live video feed preview */}
          <div style={{
            height: '160px',
            backgroundColor: 'rgba(0, 0, 0, 0.3)',
            borderRadius: '8px',
            border: '1px solid var(--border)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            position: 'relative',
            overflow: 'hidden'
          }}>
            {camera.status === 'online' || camera.status === 'connecting' ? (
              <>
                <img 
                  src={`/api/v1/cameras/${camera.id}/stream`} 
                  alt={camera.name}
                  style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                  onError={(e) => {
                    // Falls back to camera icon on error
                    (e.target as HTMLElement).style.display = 'none';
                  }}
                />
                <div style={{
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  right: 0,
                  bottom: 0,
                  backgroundColor: 'rgba(0, 0, 0, 0.4)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  opacity: 0,
                  transition: 'opacity 0.2s',
                }}
                className="hover-overlay"
                onMouseEnter={(e) => e.currentTarget.style.opacity = '1'}
                onMouseLeave={(e) => e.currentTarget.style.opacity = '0'}
                >
                  <PlayCircle size={40} style={{ color: 'white' }} />
                </div>
              </>
            ) : (
              <CameraIcon size={32} style={{ color: 'var(--text-muted)' }} />
            )}
            
            {/* Stream Type Label */}
            <span style={{
              position: 'absolute',
              bottom: '8px',
              left: '8px',
              background: 'rgba(0, 0, 0, 0.6)',
              fontSize: '0.7rem',
              padding: '2px 6px',
              borderRadius: '4px',
              textTransform: 'uppercase',
              color: 'var(--text-secondary)'
            }}>
              {camera.type}
            </span>
          </div>

          {/* Zones count */}
          <div style={{ marginTop: '12px', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
            Configured Zones: {camera.config_json?.zones?.length || 0}
          </div>
        </div>
      ))}
    </div>
  );
};

export default CameraGrid;
