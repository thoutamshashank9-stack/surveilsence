import React, { useState, useEffect } from 'react';
import { Users, Video, ShieldAlert, Clock } from 'lucide-react';
import api from '../services/api';
import useCameraStore from '../store/cameraStore';
import useAlertStore from '../store/alertStore';
import KPICard from '../components/dashboard/KPICard';
import CameraGrid from '../components/dashboard/CameraGrid';
import AlertCard from '../components/alerts/AlertCard';
import LoadingSpinner from '../components/common/LoadingSpinner';

export const Dashboard: React.FC = () => {
  const [loading, setLoading] = useState<boolean>(true);
  const [stats, setStats] = useState<any>({ total_entries: 0, total_exits: 0 });
  const { cameras, setCameras } = useCameraStore();
  const { alerts, setAlerts, acknowledgeAlert } = useAlertStore();

  useEffect(() => {
    const fetchData = async () => {
      try {
        // Fetch cameras
        const cams = await api.getCameras();
        setCameras(cams);

        // Fetch recent alerts
        const activeAlerts = await api.getAlerts({ limit: 5 });
        setAlerts(activeAlerts);

        // Fetch stats if camera exists
        if (cams.length > 0) {
          const res = await api.getFootfall(cams[0].id);
          setStats(res);
        }
      } catch (err) {
        console.error('Failed to load dashboard data:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [setCameras, setAlerts]);

  const handleAcknowledge = async (id: number, acknowledged_by: string, notes?: string) => {
    try {
      const acked = await api.acknowledgeAlert(id, acknowledged_by, notes);
      acknowledgeAlert(id, acked);
    } catch (err) {
      console.error(err);
    }
  };

  if (loading) return <LoadingSpinner />;

  const activeCamsCount = cameras.filter((c) => c.status === 'online').length;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* 4 KPI cards grid */}
      <div className="grid-cols-4">
        <KPICard 
          title="Total Store Entries" 
          value={stats.total_entries} 
          change="+12.4%" 
          icon={Users} 
          colorClass="blue" 
        />
        <KPICard 
          title="Active Edge Streams" 
          value={`${activeCamsCount}/${cameras.length}`} 
          icon={Video} 
          colorClass="emerald" 
        />
        <KPICard 
          title="Triggered Alerts" 
          value={alerts.filter((a) => a.status === 'active').length} 
          change="-4.2%" 
          isPositive={false}
          icon={ShieldAlert} 
          colorClass="amber" 
        />
        <KPICard 
          title="Avg Dwell Time" 
          value="4.8 min" 
          change="+8.1%" 
          icon={Clock} 
          colorClass="purple" 
        />
      </div>

      {/* Main panel layout */}
      <div style={{ display: 'flex', gap: '24px', flexWrap: 'wrap' }}>
        {/* Left side: Cameras grid */}
        <div style={{ flexGrow: 2, flexBasis: '500px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h2 style={{ fontSize: '1.1rem', fontWeight: 600 }}>Active Stream Feeds</h2>
          </div>
          <CameraGrid cameras={cameras} />
        </div>

        {/* Right side: Alert feed */}
        <div style={{ flexGrow: 1, flexBasis: '320px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <h2 style={{ fontSize: '1.1rem', fontWeight: 600 }}>Recent Incidents</h2>
          {alerts.length === 0 ? (
            <div className="card" style={{ textAlign: 'center', padding: '30px', color: 'var(--text-muted)' }}>
              No recent security incidents triggered.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {alerts.slice(0, 3).map((alert) => (
                <AlertCard 
                  key={alert.id} 
                  alert={alert} 
                  onAcknowledge={handleAcknowledge} 
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
export default Dashboard;
