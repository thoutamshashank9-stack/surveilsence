import React, { useState, useEffect } from 'react';
import { ShieldAlert, RefreshCw, Filter } from 'lucide-react';
import api from '../services/api';
import useAlertStore from '../store/alertStore';
import AlertCard from '../components/alerts/AlertCard';
import LoadingSpinner from '../components/common/LoadingSpinner';


export const Alerts: React.FC = () => {
  const [loading, setLoading] = useState<boolean>(true);
  const [severityFilter, setSeverityFilter] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('active');
  const [stats, setStats] = useState<any>(null);
  
  const { alerts, setAlerts, acknowledgeAlert } = useAlertStore();

  const fetchAlerts = async () => {
    setLoading(true);
    try {
      const activeAlerts = await api.getAlerts({
        severity: severityFilter || undefined,
        status: statusFilter || undefined,
        limit: 50
      });
      setAlerts(activeAlerts);
      
      const resStats = await api.getAlertStats();
      setStats(resStats);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAlerts();
  }, [severityFilter, statusFilter]);

  const handleAcknowledge = async (id: number, acknowledged_by: string, notes?: string) => {
    try {
      const acked = await api.acknowledgeAlert(id, acknowledged_by, notes);
      acknowledgeAlert(id, acked);
      // Reload stats
      const resStats = await api.getAlertStats();
      setStats(resStats);
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Stats Summary banner */}
      {stats && (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
          gap: '16px'
        }}>
          <div className="card" style={{ padding: '16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Active Alerts</div>
              <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: 'var(--accent-red)' }}>{stats.active_count}</div>
            </div>
            <ShieldAlert size={28} style={{ color: 'var(--accent-red)', opacity: 0.8 }} />
          </div>
          <div className="card" style={{ padding: '16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Acknowledged</div>
              <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: 'var(--accent-emerald)' }}>{stats.acknowledged_count}</div>
            </div>
            <ShieldAlert size={28} style={{ color: 'var(--accent-emerald)', opacity: 0.8 }} />
          </div>
          <div className="card" style={{ padding: '16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Critical Priority</div>
              <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: 'var(--accent-red)' }}>
                {stats.by_severity?.critical || 0}
              </div>
            </div>
          </div>
          <div className="card" style={{ padding: '16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Warning Priority</div>
              <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: 'var(--accent-amber)' }}>
                {stats.by_severity?.warning || 0}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Filter panel */}
      <div className="card" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px', padding: '14px 20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Filter size={16} style={{ color: 'var(--text-muted)' }} />
            <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Filters:</span>
          </div>

          <select 
            className="select"
            style={{ width: '150px', padding: '6px 12px' }}
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="">All Statuses</option>
            <option value="active">Active</option>
            <option value="acknowledged">Acknowledged</option>
          </select>

          <select 
            className="select"
            style={{ width: '150px', padding: '6px 12px' }}
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
          >
            <option value="">All Severities</option>
            <option value="critical">Critical</option>
            <option value="warning">Warning</option>
            <option value="info">Info</option>
          </select>
        </div>

        <button className="btn btn-ghost" style={{ padding: '8px 14px' }} onClick={fetchAlerts}>
          <RefreshCw size={14} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Alerts Feed */}
      {loading ? (
        <LoadingSpinner />
      ) : alerts.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: '60px', color: 'var(--text-muted)' }}>
          No security incident logs match selected filters.
        </div>
      ) : (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(360px, 1fr))',
          gap: '20px'
        }}>
          {alerts.map((alert) => (
            <AlertCard 
              key={alert.id}
              alert={alert}
              onAcknowledge={handleAcknowledge}
            />
          ))}
        </div>
      )}
    </div>
  );
};
export default Alerts;
