import React, { useState } from 'react';
import { AlertTriangle, ShieldCheck, Clock } from 'lucide-react';
import { Alert } from '../../types';

interface AlertCardProps {
  alert: Alert;
  onAcknowledge?: (id: number, acknowledged_by: string, notes?: string) => Promise<void>;
}

export const AlertCard: React.FC<AlertCardProps> = ({ alert, onAcknowledge }) => {
  const [ackName, setAckName] = useState<string>('operator');
  const [showAckForm, setShowAckForm] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(false);

  const getBorderColor = () => {
    switch (alert.severity) {
      case 'critical':
      case 'emergency': return 'var(--accent-red)';
      case 'warning': return 'var(--accent-amber)';
      default: return 'var(--accent-blue)';
    }
  };

  const getBadgeClass = () => {
    switch (alert.severity) {
      case 'critical':
      case 'emergency': return 'badge-critical';
      case 'warning': return 'badge-warning';
      default: return 'badge-info';
    }
  };

  const handleAcknowledgeSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!onAcknowledge) return;
    setLoading(true);
    try {
      await onAcknowledge(alert.id, ackName, 'Acknowledged via Dashboard UI');
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
      setShowAckForm(false);
    }
  };

  return (
    <div 
      className="card fade-in"
      style={{
        borderLeft: `4px solid ${getBorderColor()}`,
        display: 'flex',
        flexDirection: 'column',
        gap: '12px',
        padding: '16px'
      }}
    >
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span className={`badge ${getBadgeClass()}`}>{alert.severity}</span>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            ID: #{alert.id}
          </span>
        </div>
        
        {/* Status */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem' }}>
          <Clock size={12} style={{ color: 'var(--text-muted)' }} />
          <span style={{ color: 'var(--text-secondary)' }}>
            {new Date(alert.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
          </span>
        </div>
      </div>

      {/* Description */}
      <div>
        <p style={{ fontSize: '0.9rem', fontWeight: 500, color: 'var(--text-primary)', marginBottom: '4px' }}>
          {alert.description}
        </p>
        <div style={{ display: 'flex', gap: '12px', fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
          <span>Camera: {alert.camera_id}</span>
          {alert.zone_name && <span>Zone: {alert.zone_name}</span>}
          {alert.track_id && <span>Target: P{alert.track_id}</span>}
        </div>
        
        {alert.metadata_json?.vlm_description && (
          <div style={{
            marginTop: '10px',
            padding: '10px 14px',
            background: 'rgba(255,255,255,0.02)',
            borderRadius: '6px',
            borderLeft: '3px solid var(--accent-purple)',
            fontSize: '0.78rem',
            color: 'var(--text-secondary)',
            lineHeight: '1.4'
          }}>
            <span style={{ fontWeight: 600, color: 'var(--accent-purple)', display: 'block', marginBottom: '4px', textTransform: 'uppercase', fontSize: '0.65rem', letterSpacing: '0.05em' }}>
              VLM Context Verification
            </span>
            {alert.metadata_json.vlm_description}
          </div>
        )}
      </div>

      {/* Footer / Actions */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        borderTop: '1px solid var(--border)',
        paddingTop: '12px',
        marginTop: '4px'
      }}>
        {alert.status === 'active' ? (
          <>
            {!showAckForm ? (
              <button 
                className="btn btn-ghost"
                style={{ padding: '6px 12px', fontSize: '0.75rem' }}
                onClick={() => setShowAckForm(true)}
              >
                <AlertTriangle size={14} />
                <span>Acknowledge Alert</span>
              </button>
            ) : (
              <form onSubmit={handleAcknowledgeSubmit} style={{ display: 'flex', gap: '8px', width: '100%' }}>
                <input 
                  type="text"
                  className="input"
                  style={{ padding: '6px 10px', fontSize: '0.75rem', maxWidth: '180px' }}
                  placeholder="Operator username"
                  value={ackName}
                  onChange={(e) => setAckName(e.target.value)}
                  required
                />
                <button 
                  type="submit" 
                  className="btn btn-primary"
                  style={{ padding: '6px 12px', fontSize: '0.75rem' }}
                  disabled={loading}
                >
                  Confirm
                </button>
                <button 
                  type="button" 
                  className="btn btn-ghost"
                  style={{ padding: '6px 12px', fontSize: '0.75rem' }}
                  onClick={() => setShowAckForm(false)}
                >
                  Cancel
                </button>
              </form>
            )}
          </>
        ) : (
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.75rem', color: 'var(--accent-emerald)' }}>
            <ShieldCheck size={14} />
            <span>Acknowledged by {alert.acknowledged_by}</span>
          </div>
        )}
      </div>
    </div>
  );
};
export default AlertCard;
