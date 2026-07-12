import React, { useState, useEffect } from 'react';
import { Cpu, Video, ShieldCheck, Plus, Trash2, X, AlertTriangle } from 'lucide-react';
import api from '../services/api';
import { Camera, HardwareInfo, CameraType } from '../types';
import LoadingSpinner from '../components/common/LoadingSpinner';

export const Settings: React.FC = () => {
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [hardware, setHardware] = useState<HardwareInfo | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  // Form Modal States
  const [showAddModal, setShowAddModal] = useState<boolean>(false);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string>('');

  // New Camera Form Data
  const [formData, setFormData] = useState({
    id: '',
    name: '',
    source: '',
    type: 'http' as CameraType,
    enabled: true,
    stream_type: 'sub',
    fps_cap: 30,
  });

  const fetchSettings = async () => {
    try {
      const cams = await api.getCameras();
      setCameras(cams);
      const hw = await api.getHardware();
      setHardware(hw);
    } catch (err: any) {
      console.error('Failed to load settings:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSettings();
  }, []);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value, type } = e.target;
    let val: any = value;
    if (type === 'checkbox') {
      val = (e.target as HTMLInputElement).checked;
    } else if (name === 'fps_cap') {
      val = parseInt(value, 10) || 30;
    }
    setFormData((prev) => ({ ...prev, [name]: val }));
  };

  const handleOpenAddModal = () => {
    setFormData({
      id: '',
      name: '',
      source: '',
      type: 'http',
      enabled: true,
      stream_type: 'sub',
      fps_cap: 30,
    });
    setError('');
    setShowAddModal(true);
  };

  const handleAddCamera = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    // Quick validation
    if (!formData.id.trim()) return setError('Camera ID is required');
    if (!formData.name.trim()) return setError('Camera name is required');
    if (!formData.source.trim()) return setError('Camera source/link is required');

    setSubmitting(true);
    try {
      // Build camera model matching create schema
      const payload = {
        id: formData.id.trim(),
        name: formData.name.trim(),
        source: formData.source.trim(),
        type: formData.type,
        enabled: formData.enabled,
        stream_type: formData.stream_type,
        fps_cap: formData.fps_cap,
        zones: [] // Starts with empty zones list
      };

      await api.createCamera(payload);
      setShowAddModal(false);
      
      // Reload camera list
      await fetchSettings();
    } catch (err: any) {
      setError(err.message || 'Failed to add camera feed');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteCamera = async (id: string) => {
    if (!window.confirm(`Are you sure you want to delete camera "${id}"? This will permanently remove its historical records.`)) {
      return;
    }

    try {
      setLoading(true);
      await api.deleteCamera(id);
      await fetchSettings();
    } catch (err: any) {
      alert(err.message || 'Failed to delete camera feed');
      setLoading(false);
    }
  };

  if (loading) return <LoadingSpinner />;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      
      {/* 1. Camera Config Card */}
      <div className="card" style={{ padding: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <h2 style={{ fontSize: '1rem', fontWeight: 600, margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Video size={18} style={{ color: 'var(--accent-blue)' }} />
            <span>Configured Camera Feeds ({cameras.length})</span>
          </h2>
          <button 
            className="btn btn-primary" 
            style={{ padding: '8px 16px' }}
            onClick={handleOpenAddModal}
          >
            <Plus size={16} />
            <span>Add Camera</span>
          </button>
        </div>

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
                <th style={{ padding: '12px', textAlign: 'right' }}>Actions</th>
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
                  <td style={{ padding: '12px' }}>{c.config_json?.zones?.length || 0} Zones</td>
                  <td style={{ padding: '12px', textAlign: 'right' }}>
                    <button 
                      className="btn btn-ghost" 
                      style={{ padding: '6px 10px', color: 'var(--accent-red)', borderColor: 'rgba(239, 68, 68, 0.2)' }}
                      onClick={() => handleDeleteCamera(c.id)}
                      title="Delete camera feed"
                    >
                      <Trash2 size={14} />
                    </button>
                  </td>
                </tr>
              ))}
              {cameras.length === 0 && (
                <tr>
                  <td colSpan={7} style={{ padding: '30px', textAlign: 'center', color: 'var(--text-muted)' }}>
                    No camera feeds configured. Add a camera to start analytics.
                  </td>
                </tr>
              )}
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

      {/* 3. Add Camera Modal Form */}
      {showAddModal && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.75)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000,
          padding: '20px'
        }}>
          <div className="card fade-in" style={{
            width: '100%',
            maxWidth: '500px',
            backgroundColor: 'var(--bg-secondary)',
            padding: '28px',
            boxShadow: '0 20px 50px rgba(0, 0, 0, 0.6)',
            display: 'flex',
            flexDirection: 'column',
            gap: '20px',
            border: '1px solid var(--border)'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3 style={{ fontSize: '1.1rem', fontWeight: 600, margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Plus size={18} style={{ color: 'var(--accent-blue)' }} />
                <span>Add Camera Stream</span>
              </h3>
              <button 
                className="btn btn-ghost" 
                style={{ padding: '4px', borderRadius: '50%', border: 'none' }}
                onClick={() => setShowAddModal(false)}
              >
                <X size={18} />
              </button>
            </div>

            {error && (
              <div style={{
                backgroundColor: 'rgba(239, 68, 68, 0.1)',
                border: '1px solid rgba(239, 68, 68, 0.25)',
                color: 'var(--accent-red)',
                borderRadius: '8px',
                padding: '12px',
                fontSize: '0.8rem',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}>
                <AlertTriangle size={16} />
                <span>{error}</span>
              </div>
            )}

            <form onSubmit={handleAddCamera} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Camera ID (unique, e.g. phone_cam_01)</label>
                <input 
                  type="text" 
                  name="id" 
                  className="input" 
                  placeholder="phone_cam_01" 
                  value={formData.id}
                  onChange={handleInputChange}
                  required
                />
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Camera Name</label>
                <input 
                  type="text" 
                  name="name" 
                  className="input" 
                  placeholder="IP Phone Camera" 
                  value={formData.name}
                  onChange={handleInputChange}
                  required
                />
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Source Link (RTSP/HTTP MJPEG URL or File Path)</label>
                <input 
                  type="text" 
                  name="source" 
                  className="input" 
                  placeholder="http://192.168.1.50:8080/video" 
                  value={formData.source}
                  onChange={handleInputChange}
                  required
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Camera Type</label>
                  <select name="type" className="select" value={formData.type} onChange={handleInputChange}>
                    <option value="http">HTTP (MJPEG)</option>
                    <option value="rtsp">RTSP (H.264)</option>
                    <option value="usb">USB Camera</option>
                    <option value="file">Local File</option>
                    <option value="mock">Simulated Mock</option>
                  </select>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>FPS Target Cap</label>
                  <input 
                    type="number" 
                    name="fps_cap" 
                    className="input" 
                    min="1" 
                    max="60" 
                    value={formData.fps_cap}
                    onChange={handleInputChange}
                  />
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '12px' }}>
                <button 
                  type="button" 
                  className="btn btn-ghost" 
                  onClick={() => setShowAddModal(false)}
                  disabled={submitting}
                >
                  Cancel
                </button>
                <button 
                  type="submit" 
                  className="btn btn-primary" 
                  disabled={submitting}
                >
                  {submitting ? 'Adding...' : 'Register Camera'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
export default Settings;
