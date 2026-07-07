import React, { useState, useEffect } from 'react';
import { ResponsiveContainer, LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts';
import { LineChart as ChartIcon, FileSpreadsheet, RefreshCw } from 'lucide-react';
import api from '../services/api';
import { Camera, FootfallMetrics, DwellMetrics } from '../types';
import LoadingSpinner from '../components/common/LoadingSpinner';

export const Analytics: React.FC = () => {
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [selectedCamId, setSelectedCamId] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(true);
  
  const [footfallData, setFootfallData] = useState<FootfallMetrics | null>(null);
  const [dwellData, setDwellData] = useState<DwellMetrics | null>(null);
  
  const [dateStr, setDateStr] = useState<string>(() => {
    return new Date().toISOString().split('T')[0];
  });

  useEffect(() => {
    const fetchCameras = async () => {
      try {
        const cams = await api.getCameras();
        setCameras(cams);
        if (cams.length > 0) {
          setSelectedCamId(cams[0].id);
        }
      } catch (err) {
        console.error(err);
      }
    };
    fetchCameras();
  }, []);

  const fetchAnalytics = async () => {
    if (!selectedCamId) return;
    setLoading(true);
    try {
      const f_data = await api.getFootfall(selectedCamId, dateStr);
      setFootfallData(f_data);
      
      const d_data = await api.getDwellStats(selectedCamId, dateStr);
      setDwellData(d_data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalytics();
  }, [selectedCamId, dateStr]);

  const handleExport = () => {
    if (!selectedCamId) return;
    window.open(`/api/v1/analytics/export?camera_id=${selectedCamId}&date=${dateStr}`, '_blank');
  };

  if (loading && !footfallData) return <LoadingSpinner />;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Control bar */}
      <div className="card" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px', padding: '14px 20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px', flexWrap: 'wrap' }}>
          {/* Camera Selector */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Camera:</span>
            <select 
              className="select"
              style={{ width: '180px', padding: '6px 12px' }}
              value={selectedCamId}
              onChange={(e) => setSelectedCamId(e.target.value)}
            >
              {cameras.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </div>

          {/* Date Picker */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Date:</span>
            <input 
              type="date"
              className="input"
              style={{ width: '160px', padding: '5px 12px' }}
              value={dateStr}
              onChange={(e) => setDateStr(e.target.value)}
            />
          </div>
        </div>

        {/* Export and Refresh */}
        <div style={{ display: 'flex', gap: '12px' }}>
          <button className="btn btn-ghost" style={{ padding: '8px 14px' }} onClick={handleExport} disabled={!selectedCamId}>
            <FileSpreadsheet size={14} />
            <span>Export CSV</span>
          </button>
          
          <button className="btn btn-ghost" style={{ padding: '8px 14px' }} onClick={fetchAnalytics}>
            <RefreshCw size={14} />
          </button>
        </div>
      </div>

      {loading ? (
        <LoadingSpinner />
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          {/* 1. Footfall Hourly Line Chart */}
          <div className="card" style={{ padding: '24px' }}>
            <h2 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <ChartIcon size={18} style={{ color: 'var(--accent-blue)' }} />
              <span>Footfall Hourly Traffic Trends (Entries & Exits)</span>
            </h2>
            
            <div style={{ width: '100%', height: '300px' }}>
              {footfallData && footfallData.hourly_trends.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={footfallData.hourly_trends} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                    <XAxis dataKey="hour" stroke="var(--text-muted)" fontSize={11} />
                    <YAxis stroke="var(--text-muted)" fontSize={11} />
                    <Tooltip 
                      contentStyle={{ background: 'var(--bg-secondary)', borderColor: 'var(--border)', color: 'var(--text-primary)' }}
                      labelStyle={{ color: 'var(--text-secondary)' }}
                    />
                    <Legend wrapperStyle={{ fontSize: 12, paddingTop: 10 }} />
                    <Line type="monotone" dataKey="entries" name="Entries" stroke="var(--accent-emerald)" strokeWidth={2} dot={false} />
                    <Line type="monotone" dataKey="exits" name="Exits" stroke="var(--accent-blue)" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <div style={{ textAlign: 'center', paddingTop: '100px', color: 'var(--text-muted)' }}>No footfall trend data recorded.</div>
              )}
            </div>
          </div>

          {/* 2. Zone Dwell Bar Chart */}
          <div className="card" style={{ padding: '24px' }}>
            <h2 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <ChartIcon size={18} style={{ color: 'var(--accent-purple)' }} />
              <span>Zone Customer Dwell Timings</span>
            </h2>
            
            <div style={{ width: '100%', height: '300px' }}>
              {dwellData && dwellData.zones.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={dwellData.zones} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                    <XAxis dataKey="zone_name" stroke="var(--text-muted)" fontSize={11} />
                    <YAxis name="Seconds" stroke="var(--text-muted)" fontSize={11} />
                    <Tooltip 
                      contentStyle={{ background: 'var(--bg-secondary)', borderColor: 'var(--border)', color: 'var(--text-primary)' }}
                    />
                    <Legend wrapperStyle={{ fontSize: 12, paddingTop: 10 }} />
                    <Bar dataKey="avg_dwell_seconds" name="Avg Dwell (s)" fill="var(--accent-purple)" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="max_dwell_seconds" name="Max Dwell (s)" fill="var(--accent-amber)" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div style={{ textAlign: 'center', paddingTop: '100px', color: 'var(--text-muted)' }}>No dwell time logs recorded for this date.</div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
export default Analytics;
