import React, { useState, useEffect } from 'react';
import { Cpu, Video, ShieldCheck, Plus, Trash2, X, AlertTriangle, Edit2, Bell } from 'lucide-react';
import api from '../services/api';
import { Camera, HardwareInfo, CameraType } from '../types';
import LoadingSpinner from '../components/common/LoadingSpinner';

export const Settings: React.FC = () => {
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [hardware, setHardware] = useState<HardwareInfo | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  // Form Modal States
  const [showAddModal, setShowAddModal] = useState<boolean>(false);
  const [isEditMode, setIsEditMode] = useState<boolean>(false);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string>('');
  const [formZones, setFormZones] = useState<any[]>([]);

  // Visual Zone Painter States
  const [visualEditing, setVisualEditing] = useState<boolean>(false);
  const [streamActive, setStreamActive] = useState<boolean>(true);
  const [frozenImage, setFrozenImage] = useState<string | null>(null);
  const [activeRectPoints, setActiveRectPoints] = useState<number[][]>([
    [100, 100], [500, 100], [500, 500], [100, 500]
  ]);
  const [draggingPointIndex, setDraggingPointIndex] = useState<number | null>(null);
  
  // Zone metadata form
  const [zoneType, setZoneType] = useState<string>('worker_cabin');
  const [customZoneName, setCustomZoneName] = useState<string>('');
  const [empName, setEmpName] = useState<string>('');
  const [empId, setEmpId] = useState<string>('');
  const [showBoxOverlay, setShowBoxOverlay] = useState<boolean>(false);

  const imgRef = React.useRef<HTMLImageElement | null>(null);
  const canvasRef = React.useRef<HTMLCanvasElement | null>(null);
  const containerRef = React.useRef<HTMLDivElement | null>(null);

  // New/Edit Camera Form Data
  const [formData, setFormData] = useState({
    id: '',
    name: '',
    source: '',
    type: 'http' as CameraType,
    enabled: true,
    stream_type: 'sub',
    fps_cap: 30,
  });



  // Global Notification States
  const [notificationsConfig, setNotificationsConfig] = useState({
    telegram: { enabled: false, bot_token: '', chat_id: '' },
    whatsapp: { enabled: false, provider: 'twilio', account_sid: '', auth_token: '', from_number: '', to_number: '', instance_id: '', token: '' },
    email: { enabled: false, smtp_host: '', smtp_port: 587 }
  });
  const [savingNotifications, setSavingNotifications] = useState<boolean>(false);
  const [notificationMessage, setNotificationMessage] = useState<string>('');
  const [notificationError, setNotificationError] = useState<string>('');

  // AI Model Selector States
  const [activeModel, setActiveModel] = useState<string>('rtdetrv2_r18');
  const [modelLoading, setModelLoading] = useState<boolean>(false);
  const [modelMessage, setModelMessage] = useState<string>('');

  const MODEL_SPECS: Record<string, { label: string; input: string; license: string; description: string }> = {
    rtdetrv2_r18: {
      label: 'RT-DETRv2 ResNet-18 (Primary — Balanced)',
      input: '640 × 640',
      license: 'Apache-2.0',
      description: 'Real-Time Detection Transformer'
    },
    rfdetr_nano: {
      label: 'RF-DETR Nano (High Accuracy)',
      input: '384 × 384',
      license: 'Apache-2.0',
      description: 'Ultra-fast Transformer Detector'
    }
  };

  const fetchModelInfo = async () => {
    try {
      const res = await fetch('/api/v1/system/detection-model');
      if (res.ok) {
        const data = await res.json();
        if (data.model) setActiveModel(data.model);
      }
    } catch (err) {
      console.error('Failed to fetch detection model info:', err);
    }
  };

  const switchModel = async (modelName: string) => {
    setModelLoading(true);
    setModelMessage('');
    try {
      const res = await fetch('/api/v1/system/detection-model', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model: modelName })
      });
      if (res.ok) {
        setActiveModel(modelName);
        setModelMessage(`✓ Switched to ${MODEL_SPECS[modelName]?.label || modelName}`);
      } else {
        const errData = await res.json().catch(() => ({}));
        setModelMessage(`✗ Failed: ${errData.detail || res.statusText}`);
      }
    } catch (err: any) {
      setModelMessage(`✗ Error: ${err.message || 'Network request failed'}`);
    } finally {
      setModelLoading(false);
    }
  };

  const fetchSettings = async () => {
    try {
      const cams = await api.getCameras();
      setCameras(cams);
      const hw = await api.getHardware();
      setHardware(hw);
      const notif = await api.getNotifications();
      if (notif) {
        setNotificationsConfig({
          telegram: {
            enabled: notif.telegram?.enabled ?? false,
            bot_token: notif.telegram?.bot_token ?? '',
            chat_id: notif.telegram?.chat_id ?? ''
          },
          whatsapp: {
            enabled: notif.whatsapp?.enabled ?? false,
            provider: notif.whatsapp?.provider ?? 'twilio',
            account_sid: notif.whatsapp?.account_sid ?? '',
            auth_token: notif.whatsapp?.auth_token ?? '',
            from_number: notif.whatsapp?.from_number ?? '',
            to_number: notif.whatsapp?.to_number ?? '',
            instance_id: notif.whatsapp?.instance_id ?? '',
            token: notif.whatsapp?.token ?? ''
          },
          email: {
            enabled: notif.email?.enabled ?? false,
            smtp_host: notif.email?.smtp_host ?? '',
            smtp_port: notif.email?.smtp_port ?? 587
          }
        });
      }
      await fetchModelInfo();
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

  const handleNotificationChange = (channel: 'telegram' | 'whatsapp' | 'email', field: string, value: any) => {
    setNotificationsConfig((prev: any) => ({
      ...prev,
      [channel]: {
        ...prev[channel],
        [field]: value
      }
    }));
  };

  const getBbox = (points: number[][]) => {
    if (!points || points.length === 0) return { xMin: 0, yMin: 0, xMax: 100, yMax: 100 };
    const xs = points.map(p => p[0]);
    const ys = points.map(p => p[1]);
    return {
      xMin: Math.min(...xs),
      yMin: Math.min(...ys),
      xMax: Math.max(...xs),
      yMax: Math.max(...ys)
    };
  };

  const handleZoneChange = (index: number, field: string, value: any) => {
    const updated = [...formZones];
    if (field === 'xMin' || field === 'yMin' || field === 'xMax' || field === 'yMax') {
      const currentBbox = getBbox(updated[index].points);
      const newBbox = { ...currentBbox, [field]: Number(value) };
      updated[index].points = [
        [newBbox.xMin, newBbox.yMin],
        [newBbox.xMax, newBbox.yMin],
        [newBbox.xMax, newBbox.yMax],
        [newBbox.xMin, newBbox.yMax]
      ];
    } else if (field === 'restricted') {
      updated[index] = { ...updated[index], [field]: Boolean(value) };
    } else {
      updated[index] = { ...updated[index], [field]: value };
    }
    setFormZones(updated);
  };

  const handleAddZone = () => {
    setFormZones([
      ...formZones,
      {
        name: `zone_${formZones.length + 1}`,
        type: 'polygon',
        points: [[100, 100], [500, 100], [500, 500], [100, 500]],
        restricted: false
      }
    ]);
  };

  const handleDeleteZone = (index: number) => {
    setFormZones(formZones.filter((_, idx) => idx !== index));
  };

  const handleFreezeFrame = () => {
    if (imgRef.current && canvasRef.current) {
      const img = imgRef.current;
      const canvas = canvasRef.current;
      canvas.width = img.naturalWidth || 640;
      canvas.height = img.naturalHeight || 480;
      const ctx = canvas.getContext('2d');
      if (ctx) {
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
        setFrozenImage(canvas.toDataURL('image/jpeg'));
        setStreamActive(false);
      }
    }
  };

  const handlePointerDown = (index: number, e: React.PointerEvent) => {
    e.preventDefault();
    setDraggingPointIndex(index);
    (e.target as Element).setPointerCapture(e.pointerId);
  };

  const handlePointerMove = (e: React.PointerEvent) => {
    if (draggingPointIndex === null || !containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    let x = e.clientX - rect.left;
    let y = e.clientY - rect.top;
    x = Math.max(0, Math.min(x, rect.width));
    y = Math.max(0, Math.min(y, rect.height));

    const imgWidth = canvasRef.current?.width || 640;
    const imgHeight = canvasRef.current?.height || 480;
    const scaleX = imgWidth / rect.width;
    const scaleY = imgHeight / rect.height;

    const nativeX = Math.round(x * scaleX);
    const nativeY = Math.round(y * scaleY);

    const updated = [...activeRectPoints];
    updated[draggingPointIndex] = [nativeX, nativeY];

    // Align rectangle corners constraint
    if (draggingPointIndex === 0) {
      updated[1][1] = nativeY;
      updated[3][0] = nativeX;
    } else if (draggingPointIndex === 1) {
      updated[0][1] = nativeY;
      updated[2][0] = nativeX;
    } else if (draggingPointIndex === 2) {
      updated[3][1] = nativeY;
      updated[1][0] = nativeX;
    } else if (draggingPointIndex === 3) {
      updated[2][1] = nativeY;
      updated[0][0] = nativeX;
    }
    setActiveRectPoints(updated);
  };

  const handlePointerUp = () => {
    if (draggingPointIndex !== null) {
      setDraggingPointIndex(null);
    }
  };

  const handleAddVisualZone = () => {
    const finalZoneName = zoneType === 'custom' ? customZoneName.trim() : zoneType;
    if (!finalZoneName) return alert('Please enter a zone name');

    const newZone = {
      name: finalZoneName,
      type: 'polygon',
      points: [...activeRectPoints],
      restricted: false,
      employee_name: zoneType === 'worker_cabin' ? empName.trim() : undefined,
      employee_id: zoneType === 'worker_cabin' ? empId.trim() : undefined
    };

    setFormZones([...formZones, newZone]);
    setVisualEditing(false);
    setStreamActive(true);
    setFrozenImage(null);
    setShowBoxOverlay(false);
    setEmpName('');
    setEmpId('');
    setCustomZoneName('');
  };

  const handleOpenAddModal = () => {
    setIsEditMode(false);
    setFormData({
      id: '',
      name: '',
      source: '',
      type: 'http',
      enabled: true,
      stream_type: 'sub',
      fps_cap: 30,
    });
    setFormZones([]);
    setVisualEditing(false);
    setStreamActive(true);
    setFrozenImage(null);
    setShowBoxOverlay(false);
    setError('');
    setShowAddModal(true);
  };

  const handleOpenEditModal = (camera: Camera) => {
    setIsEditMode(true);
    setFormData({
      id: camera.id,
      name: camera.name,
      source: camera.source,
      type: camera.type,
      enabled: camera.enabled,
      stream_type: camera.config_json?.stream_type || 'sub',
      fps_cap: camera.config_json?.fps_cap || 30,
    });
    setFormZones(camera.config_json?.zones || []);
    setVisualEditing(false);
    setStreamActive(true);
    setFrozenImage(null);
    setShowBoxOverlay(false);
    setError('');
    setShowAddModal(true);
  };


  const handleSaveCamera = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!formData.id.trim()) return setError('Camera ID is required');
    if (!formData.name.trim()) return setError('Camera name is required');
    if (!formData.source.trim()) return setError('Camera source/link is required');

    setSubmitting(true);
    try {
      const payload = {
        id: formData.id.trim(),
        name: formData.name.trim(),
        source: formData.source.trim(),
        type: formData.type,
        enabled: formData.enabled,
        stream_type: formData.stream_type,
        fps_cap: formData.fps_cap,
        zones: formZones
      };

      if (isEditMode) {
        await api.updateCamera(formData.id, payload);
      } else {
        await api.createCamera(payload);
      }
      
      setShowAddModal(false);
      await fetchSettings();
    } catch (err: any) {
      setError(err.message || `Failed to ${isEditMode ? 'update' : 'add'} camera feed`);
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

  const [testingTelegram, setTestingTelegram] = useState<boolean>(false);

  const handleTestTelegram = async () => {
    setTestingTelegram(true);
    setNotificationMessage('');
    setNotificationError('');
    try {
      const res = await fetch('/api/v1/system/notifications/test-telegram', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          bot_token: notificationsConfig.telegram.bot_token,
          chat_id: notificationsConfig.telegram.chat_id
        })
      });
      const data = await res.json();
      if (res.ok) {
        setNotificationMessage('✓ Success: Test warning snapshot sent to your Telegram bot!');
      } else {
        setNotificationError(`✗ Error: ${data.detail || 'Failed to send Telegram test image'}`);
      }
    } catch (err: any) {
      setNotificationError(`✗ Network Error: ${err.message}`);
    } finally {
      setTestingTelegram(false);
    }
  };

  const handleSaveNotifications = async (e: React.FormEvent) => {
    e.preventDefault();
    setSavingNotifications(true);
    setNotificationMessage('');
    setNotificationError('');
    try {
      await api.updateNotifications(notificationsConfig);
      setNotificationMessage('Notification settings updated! Re-applying configuration on servers...');
      setTimeout(fetchSettings, 3000);
    } catch (err: any) {
      setNotificationError(err.message || 'Failed to update notification configuration');
    } finally {
      setSavingNotifications(false);
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
                    <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
                      <button 
                        className="btn btn-ghost" 
                        style={{ padding: '6px 10px', borderColor: 'rgba(255, 255, 255, 0.1)' }}
                        onClick={() => handleOpenEditModal(c)}
                        title="Edit camera settings"
                      >
                        <Edit2 size={14} style={{ color: 'var(--accent-blue)' }} />
                      </button>
                      <button 
                        className="btn btn-ghost" 
                        style={{ padding: '6px 10px', color: 'var(--accent-red)', borderColor: 'rgba(239, 68, 68, 0.2)' }}
                        onClick={() => handleDeleteCamera(c.id)}
                        title="Delete camera feed"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
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

      {/* 2. Hardware & AI Detector details */}
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
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', fontSize: '0.85rem' }}>
            {/* Model Selector Dropdown */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <label style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Active Detection Model</label>
              <select
                className="select"
                value={activeModel}
                onChange={(e) => setActiveModel(e.target.value)}
                disabled={modelLoading}
                style={{ fontSize: '0.85rem' }}
              >
                {Object.entries(MODEL_SPECS).map(([key, spec]) => (
                  <option key={key} value={key}>{spec.label}</option>
                ))}
              </select>
            </div>

            {/* Dynamic Model Specs */}
            {MODEL_SPECS[activeModel] && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', background: 'rgba(255,255,255,0.02)', borderRadius: '8px', padding: '12px', border: '1px solid var(--border)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid rgba(255,255,255,0.03)', paddingBottom: '8px' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Description</span>
                  <span style={{ fontWeight: 'bold' }}>{MODEL_SPECS[activeModel].description}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid rgba(255,255,255,0.03)', paddingBottom: '8px' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Input Dimensions</span>
                  <span>{MODEL_SPECS[activeModel].input} px</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid rgba(255,255,255,0.03)', paddingBottom: '8px' }}>
                  <span style={{ color: 'var(--text-muted)' }}>License</span>
                  <span className="badge badge-info" style={{ fontSize: '0.65rem' }}>{MODEL_SPECS[activeModel].license}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Classes Tracked</span>
                  <span className="badge badge-info" style={{ fontSize: '0.65rem' }}>Person (COCO-0)</span>
                </div>
              </div>
            )}

            {/* Apply Button */}
            <button
              className="btn btn-primary"
              style={{ padding: '9px 20px', alignSelf: 'flex-end', opacity: modelLoading ? 0.6 : 1 }}
              disabled={modelLoading}
              onClick={() => switchModel(activeModel)}
            >
              {modelLoading ? 'Applying…' : 'Apply Model'}
            </button>

            {/* Success / Error Message */}
            {modelMessage && (
              <div style={{
                backgroundColor: modelMessage.startsWith('✓')
                  ? 'rgba(16, 185, 129, 0.1)'
                  : 'rgba(239, 68, 68, 0.1)',
                border: `1px solid ${
                  modelMessage.startsWith('✓')
                    ? 'rgba(16, 185, 129, 0.25)'
                    : 'rgba(239, 68, 68, 0.25)'
                }`,
                color: modelMessage.startsWith('✓')
                  ? 'var(--accent-emerald)'
                  : 'var(--accent-red)',
                borderRadius: '8px',
                padding: '10px 12px',
                fontSize: '0.8rem'
              }}>
                {modelMessage}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 3. Global Notification Configurations Card */}
      <div className="card" style={{ padding: '24px' }}>
        <h2 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Bell size={18} style={{ color: 'var(--accent-orange)' }} />
          <span>Alert Dispatch Channels Configuration</span>
        </h2>

        {notificationMessage && (
          <div style={{
            backgroundColor: 'rgba(16, 185, 129, 0.1)',
            border: '1px solid rgba(16, 185, 129, 0.25)',
            color: 'var(--accent-emerald)',
            borderRadius: '8px',
            padding: '12px',
            fontSize: '0.825rem',
            marginBottom: '16px'
          }}>
            {notificationMessage}
          </div>
        )}

        {notificationError && (
          <div style={{
            backgroundColor: 'rgba(239, 68, 68, 0.1)',
            border: '1px solid rgba(239, 68, 68, 0.25)',
            color: 'var(--accent-red)',
            borderRadius: '8px',
            padding: '12px',
            fontSize: '0.825rem',
            marginBottom: '16px'
          }}>
            {notificationError}
          </div>
        )}

        <form onSubmit={handleSaveNotifications} style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px', flexWrap: 'wrap' }}>
            
            {/* Telegram Channel block */}
            <div style={{ border: '1px solid var(--border)', borderRadius: '8px', padding: '16px', backgroundColor: 'rgba(255,255,255,0.01)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                <span style={{ fontWeight: 600, fontSize: '0.9rem' }}>Telegram Alerts Bot</span>
                <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem', cursor: 'pointer' }}>
                  <input 
                    type="checkbox" 
                    checked={notificationsConfig.telegram.enabled}
                    onChange={(e) => handleNotificationChange('telegram', 'enabled', e.target.checked)}
                  />
                  <span>Enable Channel</span>
                </label>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', opacity: notificationsConfig.telegram.enabled ? 1 : 0.4 }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <label style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Telegram Bot API Token</label>
                  <input 
                    type="password" 
                    className="input" 
                    placeholder="e.g. 123456789:ABCdefGhI..."
                    value={notificationsConfig.telegram.bot_token}
                    onChange={(e) => handleNotificationChange('telegram', 'bot_token', e.target.value)}
                    disabled={!notificationsConfig.telegram.enabled}
                  />
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <label style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Target Group/Chat ID</label>
                  <input 
                    type="text" 
                    className="input" 
                    placeholder="e.g. -100123456789"
                    value={notificationsConfig.telegram.chat_id}
                    onChange={(e) => handleNotificationChange('telegram', 'chat_id', e.target.value)}
                    disabled={!notificationsConfig.telegram.enabled}
                  />
                </div>
                <button
                  type="button"
                  className="btn btn-secondary"
                  style={{ padding: '7px 14px', fontSize: '0.75rem', marginTop: '6px', alignSelf: 'flex-start' }}
                  disabled={!notificationsConfig.telegram.enabled || testingTelegram}
                  onClick={handleTestTelegram}
                >
                  {testingTelegram ? 'Sending Test Warning...' : '⚡ Send Test Warning Image'}
                </button>
              </div>
            </div>

            {/* WhatsApp (Twilio) Channel block */}
            <div style={{ border: '1px solid var(--border)', borderRadius: '8px', padding: '16px', backgroundColor: 'rgba(255,255,255,0.01)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                <span style={{ fontWeight: 600, fontSize: '0.9rem' }}>WhatsApp (Twilio API)</span>
                <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem', cursor: 'pointer' }}>
                  <input 
                    type="checkbox" 
                    checked={notificationsConfig.whatsapp.enabled}
                    onChange={(e) => handleNotificationChange('whatsapp', 'enabled', e.target.checked)}
                  />
                  <span>Enable Channel</span>
                </label>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', opacity: notificationsConfig.whatsapp.enabled ? 1 : 0.4 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    <label style={{ fontSize: '0.725rem', color: 'var(--text-secondary)' }}>Twilio Account SID</label>
                    <input 
                      type="text" 
                      className="input" 
                      placeholder="AC..."
                      value={notificationsConfig.whatsapp.account_sid}
                      onChange={(e) => handleNotificationChange('whatsapp', 'account_sid', e.target.value)}
                      disabled={!notificationsConfig.whatsapp.enabled}
                    />
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    <label style={{ fontSize: '0.725rem', color: 'var(--text-secondary)' }}>Twilio Auth Token</label>
                    <input 
                      type="password" 
                      className="input" 
                      placeholder="secret..."
                      value={notificationsConfig.whatsapp.auth_token}
                      onChange={(e) => handleNotificationChange('whatsapp', 'auth_token', e.target.value)}
                      disabled={!notificationsConfig.whatsapp.enabled}
                    />
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    <label style={{ fontSize: '0.725rem', color: 'var(--text-secondary)' }}>From (whatsapp:+...)</label>
                    <input 
                      type="text" 
                      className="input" 
                      placeholder="whatsapp:+14155238886"
                      value={notificationsConfig.whatsapp.from_number}
                      onChange={(e) => handleNotificationChange('whatsapp', 'from_number', e.target.value)}
                      disabled={!notificationsConfig.whatsapp.enabled}
                    />
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    <label style={{ fontSize: '0.725rem', color: 'var(--text-secondary)' }}>To (whatsapp:+...)</label>
                    <input 
                      type="text" 
                      className="input" 
                      placeholder="whatsapp:+91..."
                      value={notificationsConfig.whatsapp.to_number}
                      onChange={(e) => handleNotificationChange('whatsapp', 'to_number', e.target.value)}
                      disabled={!notificationsConfig.whatsapp.enabled}
                    />
                  </div>
                </div>
              </div>
            </div>

          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
            <button 
              type="submit" 
              className="btn btn-primary" 
              style={{ padding: '10px 24px' }}
              disabled={savingNotifications}
            >
              {savingNotifications ? 'Saving Settings...' : 'Save Configurations'}
            </button>
          </div>
        </form>
      </div>

      {/* 4. Add/Edit Camera Modal Form */}
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
            maxWidth: '540px',
            maxHeight: '90vh',
            overflowY: 'auto',
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
                <span>{isEditMode ? 'Edit Camera Settings' : 'Add Camera Stream'}</span>
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

            <form onSubmit={handleSaveCamera} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Camera ID (unique, e.g. phone_cam_01)</label>
                <input 
                  type="text" 
                  name="id" 
                  className="input" 
                  placeholder="phone_cam_01" 
                  value={formData.id}
                  onChange={handleInputChange}
                  disabled={isEditMode}
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

              {/* Zones Configurator */}
              <div style={{ borderTop: '1px solid var(--border)', paddingTop: '16px', marginTop: '10px' }}>
                {!visualEditing ? (
                  <>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                      <h4 style={{ fontSize: '0.85rem', fontWeight: 600, margin: 0 }}>Analytical Zones (Rectangular Boxes)</h4>
                      <div style={{ display: 'flex', gap: '8px' }}>
                        <button 
                          type="button" 
                          className="btn btn-ghost" 
                          style={{ padding: '4px 10px', fontSize: '0.75rem', height: 'auto', minHeight: 'unset', color: 'var(--accent-blue)' }}
                          onClick={() => {
                            if (!formData.source) return alert('Please enter a camera source stream link first.');
                            setVisualEditing(true);
                            setStreamActive(true);
                            setFrozenImage(null);
                            setShowBoxOverlay(false);
                          }}
                        >
                          Mark Visually
                        </button>
                        <button 
                          type="button" 
                          className="btn btn-ghost" 
                          style={{ padding: '4px 10px', fontSize: '0.75rem', height: 'auto', minHeight: 'unset' }}
                          onClick={handleAddZone}
                        >
                          <Plus size={12} style={{ marginRight: '4px' }} />
                          Add Zone
                        </button>
                      </div>
                    </div>
                    
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                      {formZones.map((zone, index) => {
                        const bbox = getBbox(zone.points);
                        return (
                          <div key={index} style={{ background: 'var(--bg-primary)', padding: '12px', borderRadius: '8px', border: '1px solid var(--border)', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                              <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                                <input 
                                  type="text" 
                                  className="input" 
                                  style={{ padding: '4px 8px', fontSize: '0.8rem', width: '180px', fontWeight: 600 }}
                                  value={zone.name}
                                  placeholder="zone_name"
                                  onChange={(e) => handleZoneChange(index, 'name', e.target.value)}
                                  required
                                />
                                {zone.employee_name && (
                                  <span style={{ fontSize: '0.7rem', color: 'var(--accent-emerald)' }}>
                                    Assigned: {zone.employee_name} ({zone.employee_id})
                                  </span>
                                )}
                              </div>
                              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                                <label style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.75rem', cursor: 'pointer' }}>
                                  <input 
                                    type="checkbox" 
                                    checked={zone.restricted || false} 
                                    onChange={(e) => handleZoneChange(index, 'restricted', e.target.checked)}
                                  />
                                  Restricted
                                </label>
                                <button 
                                  type="button" 
                                  className="btn btn-ghost" 
                                  style={{ padding: '4px', color: 'var(--accent-red)' }} 
                                  onClick={() => handleDeleteZone(index)}
                                >
                                  <Trash2 size={14} />
                                </button>
                              </div>
                            </div>
                            
                            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '8px' }}>
                              <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                                <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>X Min</span>
                                <input 
                                  type="number" 
                                  className="input" 
                                  style={{ padding: '4px', fontSize: '0.8rem', textAlign: 'center' }}
                                  value={bbox.xMin}
                                  onChange={(e) => handleZoneChange(index, 'xMin', e.target.value)}
                                  required
                                />
                              </div>
                              <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                                <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Y Min</span>
                                <input 
                                  type="number" 
                                  className="input" 
                                  style={{ padding: '4px', fontSize: '0.8rem', textAlign: 'center' }}
                                  value={bbox.yMin}
                                  onChange={(e) => handleZoneChange(index, 'yMin', e.target.value)}
                                  required
                                />
                              </div>
                              <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                                <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>X Max</span>
                                <input 
                                  type="number" 
                                  className="input" 
                                  style={{ padding: '4px', fontSize: '0.8rem', textAlign: 'center' }}
                                  value={bbox.xMax}
                                  onChange={(e) => handleZoneChange(index, 'xMax', e.target.value)}
                                  required
                                />
                              </div>
                              <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                                <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Y Max</span>
                                <input 
                                  type="number" 
                                  className="input" 
                                  style={{ padding: '4px', fontSize: '0.8rem', textAlign: 'center' }}
                                  value={bbox.yMax}
                                  onChange={(e) => handleZoneChange(index, 'yMax', e.target.value)}
                                  required
                                />
                              </div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <h4 style={{ fontSize: '0.85rem', fontWeight: 600, margin: 0, color: 'var(--accent-blue)' }}>Visual Zone Editor Workspace</h4>
                      <button 
                        type="button" 
                        className="btn btn-ghost" 
                        style={{ padding: '4px 10px', fontSize: '0.75rem', height: 'auto', minHeight: 'unset' }}
                        onClick={() => setVisualEditing(false)}
                      >
                        Back to List
                      </button>
                    </div>

                    {/* Canvas & Stream Container */}
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '12px' }}>
                      <div 
                        ref={containerRef} 
                        style={{ 
                          position: 'relative', 
                          width: '100%', 
                          maxHeight: '360px',
                          aspectRatio: '16/9',
                          background: '#000', 
                          borderRadius: '8px', 
                          overflow: 'hidden',
                          border: '1px solid var(--border)'
                        }}
                      >
                        {streamActive ? (
                          <img 
                            ref={imgRef}
                            src={`/api/v1/cameras/${formData.id || 'phone cam'}/stream?t=${Date.now()}`}
                            style={{ width: '100%', height: '100%', objectFit: 'contain', display: 'block' }}
                            alt="Live Stream Preview"
                          />
                        ) : (
                          <img 
                            src={frozenImage || ''}
                            style={{ width: '100%', height: '100%', objectFit: 'contain', display: 'block' }}
                            alt="Frozen snapshot"
                          />
                        )}

                        {/* Draggable Polygon Overlay */}
                        {!streamActive && showBoxOverlay && (
                          <svg 
                            style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', overflow: 'visible' }}
                            onPointerMove={handlePointerMove}
                            onPointerUp={handlePointerUp}
                          >
                            <polygon 
                              points={activeRectPoints.map(p => {
                                const imgWidth = canvasRef.current?.width || 640;
                                const imgHeight = canvasRef.current?.height || 480;
                                const rect = containerRef.current?.getBoundingClientRect();
                                const width = rect?.width || 640;
                                const height = rect?.height || 360;
                                const svgX = (p[0] / imgWidth) * width;
                                const svgY = (p[1] / imgHeight) * height;
                                return `${svgX},${svgY}`;
                              }).join(' ')} 
                              fill="rgba(59, 130, 246, 0.25)" 
                              stroke="var(--accent-blue)" 
                              strokeWidth="2.5" 
                            />
                            {activeRectPoints.map((p, idx) => {
                              const imgWidth = canvasRef.current?.width || 640;
                              const imgHeight = canvasRef.current?.height || 480;
                              const rect = containerRef.current?.getBoundingClientRect();
                              const width = rect?.width || 640;
                              const height = rect?.height || 360;
                              const svgX = (p[0] / imgWidth) * width;
                              const svgY = (p[1] / imgHeight) * height;
                              return (
                                <circle 
                                  key={idx}
                                  cx={svgX}
                                  cy={svgY}
                                  r="9"
                                  fill="white"
                                  stroke="var(--accent-blue)"
                                  strokeWidth="2.5"
                                  style={{ cursor: 'move' }}
                                  onPointerDown={(e) => handlePointerDown(idx, e)}
                                />
                              );
                            })}
                          </svg>
                        )}
                        <canvas ref={canvasRef} style={{ display: 'none' }} />
                      </div>

                      {/* Ready & adjustable options buttons */}
                      {streamActive ? (
                        <button 
                          type="button" 
                          className="btn btn-primary" 
                          style={{ width: '100%', padding: '10px' }}
                          onClick={handleFreezeFrame}
                        >
                          Ready (Take Snapshot)
                        </button>
                      ) : (
                        <div style={{ width: '100%', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                          {!showBoxOverlay ? (
                            <button 
                              type="button" 
                              className="btn btn-primary" 
                              style={{ width: '100%', padding: '10px' }}
                              onClick={() => {
                                const imgWidth = canvasRef.current?.width || 640;
                                const imgHeight = canvasRef.current?.height || 480;
                                setActiveRectPoints([
                                  [Math.round(imgWidth * 0.15), Math.round(imgHeight * 0.15)],
                                  [Math.round(imgWidth * 0.85), Math.round(imgHeight * 0.15)],
                                  [Math.round(imgWidth * 0.85), Math.round(imgHeight * 0.85)],
                                  [Math.round(imgWidth * 0.15), Math.round(imgHeight * 0.85)]
                                ]);
                                setShowBoxOverlay(true);
                              }}
                            >
                              Add Adjustable Rectangular Box
                            </button>
                          ) : (
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', background: 'var(--bg-primary)', padding: '16px', borderRadius: '8px', border: '1px solid var(--border)' }}>
                              
                              {/* Option preset selection */}
                              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                                <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Select Zone Preset / Type:</label>
                                <select 
                                  className="select" 
                                  value={zoneType} 
                                  onChange={(e) => setZoneType(e.target.value)}
                                >
                                  <option value="worker_cabin">Employee Cabin (worker_cabin)</option>
                                  <option value="conveyor_belt">Conveyor Belt (conveyor_belt)</option>
                                  <option value="bagging_area">Bagging Area (bagging_area)</option>
                                  <option value="entrance">Entrance</option>
                                  <option value="exit">Exit</option>
                                  <option value="cash_counter">Cash Counter</option>
                                  <option value="custom">Custom Zone Name</option>
                                </select>
                              </div>

                              {zoneType === 'custom' && (
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                                  <label style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Custom Zone Name:</label>
                                  <input 
                                    type="text" 
                                    className="input" 
                                    placeholder="e.g. storage_room" 
                                    value={customZoneName} 
                                    onChange={(e) => setCustomZoneName(e.target.value)} 
                                  />
                                </div>
                              )}

                              {/* If Employee Cabin is chosen, show employee metadata inputs */}
                              {zoneType === 'worker_cabin' && (
                                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                                    <label style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Employee Name:</label>
                                    <input 
                                      type="text" 
                                      className="input" 
                                      placeholder="e.g. Shashank Thoutam" 
                                      value={empName}
                                      onChange={(e) => setEmpName(e.target.value)}
                                      required
                                    />
                                  </div>
                                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                                    <label style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Employee ID / Code:</label>
                                    <input 
                                      type="text" 
                                      className="input" 
                                      placeholder="e.g. EMP_101" 
                                      value={empId}
                                      onChange={(e) => setEmpId(e.target.value)}
                                      required
                                    />
                                  </div>
                                </div>
                              )}

                              <div style={{ display: 'flex', gap: '10px', marginTop: '6px' }}>
                                <button 
                                  type="button" 
                                  className="btn btn-ghost" 
                                  style={{ flex: 1 }}
                                  onClick={() => setStreamActive(true)}
                                >
                                  Recapture Video
                                </button>
                                <button 
                                  type="button" 
                                  className="btn btn-primary" 
                                  style={{ flex: 1 }}
                                  onClick={handleAddVisualZone}
                                >
                                  Save Zone & Enter
                                </button>
                              </div>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                )}
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
                  {submitting ? 'Saving...' : (isEditMode ? 'Update Settings' : 'Register Camera')}
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
