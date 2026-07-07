import React, { useState, useEffect } from 'react';
import { Cpu, Video, ShieldCheck } from 'lucide-react';
import api from '../services/api';
import { Camera, HardwareInfo } from '../types';
import LoadingSpinner from '../components/common/LoadingSpinner';

export const Settings: React.FC = () => {
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [hardware, setHardware] = useState<HardwareInfo | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    const fetchSettings = async () => {
      try {
        const cams = await api.getCameras();
        setCameras(cams);
        
        const hw = await api.getHardware();
        setHardware(hw);
        

      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchSettings();
  }, []);

  if (loading) return <LoadingSpinner />;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* 1. Camera Config Card */}
      <div className="card" style={{ padding: '24px' }}>
        <h2 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Video size={18} style={{ color: 'var(--accent-blue)' }} />
          <span>Configured Camera Feeds ({cameras.length})</span>
        </h2>

        <div style={{ overflowX: 'auto' }}>
          <table className="data-table" style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.875rem' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border)', color: 'var(--text-secondary)' }}>
                <th style={{ padding: '12px' }}>Camera ID</th>
                <th style={{ padding: '12px' }}>Name</th>
                <th style={{ padding: '12px' }}>Source Link</th>
                <th style={{ padding: '12px' }}>Type</th>
                <th style={{ padding: '12px' }}>Status</th>
                <th style={{ padding: '12px' }}>Zones Count</th>
              </tr>
            </thead>
            <tbody>
              {cameras.map((c) => (
                <tr key={c.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.03)', height: '48px' }}>
                  <td style={{ padding: '12px', fontWeight: 'bold' }}>{c.id}</td>
                  <td style={{ padding: '12px' }}>{c.name}</td>
                  <td style={{ padding: '12px', color: 'var(--text-muted)' }}>{c.source}</td>
                  <td style={{ padding: '12px', textTransform: 'uppercase' }}>{c.type}</td>
                  <td style={{ padding: '12px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <span className={`status-dot ${c.status === 'online' ? 'online' : 'offline'}`}></span>
                      <span style={{ textTransform: 'capitalize' }}>{c.status}</span>
                    </div>
                  </td>
                  <td style={{ padding: '12px' }}>{c.config_json.zones.length} Zones</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* 2. Hardware / Inference details */}
      <div style={{ display: 'flex', gap: '24px', flexWrap: 'wrap' }}>
        {/* Hardware Specs */}
        <div className="card" style={{ flexGrow: 1, flexBasis: '320px', padding: '24px' }}>
          <h2 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Cpu size={18} style={{ color: 'var(--accent-emerald)' }} />
            <span>Hardware & Platform Diagnostics</span>
          </h2>
          
          {hardware && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', fontSize: '0.85rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid rgba(255,255,255,0.03)', paddingBottom: '8px' }}>
                <span style={{ color: 'var(--text-muted)' }}>Host OS</span>
                <span style={{ fontWeight: 'bold' }}>{hardware.os} ({hardware.architecture})</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid rgba(255,255,255,0.03)', paddingBottom: '8px' }}>
                <span style={{ color: 'var(--text-muted)' }}>Python Engine</span>
                <span>v{hardware.python_version}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid rgba(255,255,255,0.03)', paddingBottom: '8px' }}>
                <span style={{ color: 'var(--text-muted)' }}>ONNX Runtime Version</span>
                <span>v{hardware.onnx_version}</span>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <span style={{ color: 'var(--text-muted)' }}>Execution Providers</span>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '4px' }}>
                  {hardware.available_providers.map((p) => (
                    <span 
                      key={p} 
                      className="badge badge-info" 
                      style={{ fontSize: '0.65rem', textTransform: 'none' }}
                    >
                      {p}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Inference / Model settings */}
        <div className="card" style={{ flexGrow: 1, flexBasis: '320px', padding: '24px' }}>
          <h2 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <ShieldCheck size={18} style={{ color: 'var(--accent-purple)' }} />
            <span>AI Detector Configuration</span>
          </h2>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', fontSize: '0.85rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid rgba(255,255,255,0.03)', paddingBottom: '8px' }}>
              <span style={{ color: 'var(--text-muted)' }}>Object Detector Model</span>
              <span style={{ fontWeight: 'bold' }}>RT-DETRv2 ResNet-18</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid rgba(255,255,255,0.03)', paddingBottom: '8px' }}>
              <span style={{ color: 'var(--text-muted)' }}>Model Format</span>
              <span>ONNX INT8 Quantized</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid rgba(255,255,255,0.03)', paddingBottom: '8px' }}>
              <span style={{ color: 'var(--text-muted)' }}>Classes Tracked</span>
              <span className="badge badge-info" style={{ fontSize: '0.65rem' }}>Person (COCO-0)</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid rgba(255,255,255,0.03)', paddingBottom: '8px' }}>
              <span style={{ color: 'var(--text-muted)' }}>Input Dimensions</span>
              <span>640 x 640 px (Letterboxed)</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-muted)' }}>Confidence Threshold</span>
              <span>0.35</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
export default Settings;
