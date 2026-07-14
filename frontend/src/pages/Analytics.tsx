import React, { useState, useEffect } from 'react';
import { ResponsiveContainer, LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts';
import { LineChart as ChartIcon, FileSpreadsheet, RefreshCw, Users, Clock, ShoppingCart, Award } from 'lucide-react';
import api from '../services/api';
import { Camera, FootfallMetrics, DwellMetrics } from '../types';
import LoadingSpinner from '../components/common/LoadingSpinner';

export const Analytics: React.FC = () => {
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [selectedCamId, setSelectedCamId] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(true);
  
  // Tabs
  const [activeTab, setActiveTab] = useState<'traffic' | 'employee'>('traffic');
  
  // Traffic Analytics data
  const [footfallData, setFootfallData] = useState<FootfallMetrics | null>(null);
  const [dwellData, setDwellData] = useState<DwellMetrics | null>(null);
  
  // Employee Analytics data
  const [shifts, setShifts] = useState<any[]>([]);
  const [interactions, setInteractions] = useState<any[]>([]);
  
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
      if (activeTab === 'traffic') {
        const f_data = await api.getFootfall(selectedCamId, dateStr);
        setFootfallData(f_data);
        
        const d_data = await api.getDwellStats(selectedCamId, dateStr);
        setDwellData(d_data);
      } else {
        const shift_data = await api.getStaffShifts(selectedCamId, dateStr);
        setShifts(shift_data);
        
        const interaction_data = await api.getStaffInteractions(selectedCamId, dateStr);
        setInteractions(interaction_data);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalytics();
  }, [selectedCamId, dateStr, activeTab]);

  const handleExport = () => {
    if (!selectedCamId) return;
    window.open(`/api/v1/analytics/export?camera_id=${selectedCamId}&date=${dateStr}`, '_blank');
  };

  // Process employee metrics helper
  const getEmployeeStats = () => {
    return shifts.map(shift => {
      const empId = shift.employee_id;
      const empInteractions = interactions.filter(i => i.employee_id === empId);
      
      const totalInteractions = empInteractions.length;
      const avgDuration = totalInteractions > 0 
        ? Math.round(empInteractions.reduce((acc, curr) => acc + curr.duration_seconds, 0) / totalInteractions) 
        : 0;
        
      const successfulConversions = empInteractions.filter(i => i.pos_ticket_id !== null).length;
      const conversionRate = totalInteractions > 0 
        ? Math.round((successfulConversions / totalInteractions) * 100) 
        : 0;

      const formatHours = (seconds: number) => {
        const h = Math.floor(seconds / 3600);
        const m = Math.floor((seconds % 3600) / 60);
        return `${h}h ${m}m`;
      };

      const formatTime = (isoString: string) => {
        const d = new Date(isoString);
        return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      };

      return {
        id: empId,
        login: formatTime(shift.first_seen),
        logout: formatTime(shift.last_seen),
        presence: formatHours(shift.total_presence_seconds),
        breakTime: formatHours(shift.total_break_seconds),
        idleTime: formatHours(shift.total_idle_seconds),
        customersServed: totalInteractions,
        avgInteraction: `${avgDuration}s`,
        conversion: `${conversionRate}%`,
        conversionVal: conversionRate
      };
    });
  };

  const processedEmployees = getEmployeeStats();

  // Metrics Highlights
  const totalInteractionsCount = interactions.length;
  const avgInteractionTimeSec = totalInteractionsCount > 0 
    ? Math.round(interactions.reduce((acc, curr) => acc + curr.duration_seconds, 0) / totalInteractionsCount)
    : 0;
  const overallConversionsCount = interactions.filter(i => i.pos_ticket_id !== null).length;
  const overallConversionRate = totalInteractionsCount > 0 
    ? Math.round((overallConversionsCount / totalInteractionsCount) * 100)
    : 0;
  const bestConvertingEmp = processedEmployees.length > 0 
    ? processedEmployees.reduce((prev, curr) => (prev.conversionVal > curr.conversionVal) ? prev : curr).id
    : 'None';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Control bar */}
      <div className="card" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px', padding: '14px 20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '24px', flexWrap: 'wrap' }}>
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

          {/* Dashboard Tabs */}
          <div style={{ display: 'flex', background: 'var(--bg-secondary)', borderRadius: '8px', padding: '3px' }}>
            <button 
              className={`btn ${activeTab === 'traffic' ? 'btn-primary' : 'btn-ghost'}`}
              style={{ padding: '6px 14px', fontSize: '0.85rem', height: 'auto', minHeight: 'unset' }}
              onClick={() => setActiveTab('traffic')}
            >
              Customer Traffic
            </button>
            <button 
              className={`btn ${activeTab === 'employee' ? 'btn-primary' : 'btn-ghost'}`}
              style={{ padding: '6px 14px', fontSize: '0.85rem', height: 'auto', minHeight: 'unset' }}
              onClick={() => setActiveTab('employee')}
            >
              Employee BI Performance
            </button>
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
      ) : activeTab === 'traffic' ? (
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
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          {/* Highlight Cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '20px' }}>
            <div className="card" style={{ padding: '20px', display: 'flex', alignItems: 'center', gap: '16px' }}>
              <div style={{ padding: '12px', background: 'rgba(59, 130, 246, 0.1)', borderRadius: '12px', color: 'var(--accent-blue)' }}>
                <Clock size={24} />
              </div>
              <div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Avg Service Duration</div>
                <div style={{ fontSize: '1.4rem', fontWeight: 700 }}>{avgInteractionTimeSec}s</div>
              </div>
            </div>

            <div className="card" style={{ padding: '20px', display: 'flex', alignItems: 'center', gap: '16px' }}>
              <div style={{ padding: '12px', background: 'rgba(16, 185, 129, 0.1)', borderRadius: '12px', color: 'var(--accent-emerald)' }}>
                <Users size={24} />
              </div>
              <div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Total Customer Interactions</div>
                <div style={{ fontSize: '1.4rem', fontWeight: 700 }}>{totalInteractionsCount}</div>
              </div>
            </div>

            <div className="card" style={{ padding: '20px', display: 'flex', alignItems: 'center', gap: '16px' }}>
              <div style={{ padding: '12px', background: 'rgba(245, 158, 11, 0.1)', borderRadius: '12px', color: 'var(--accent-amber)' }}>
                <ShoppingCart size={24} />
              </div>
              <div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Overall Conversion Rate</div>
                <div style={{ fontSize: '1.4rem', fontWeight: 700 }}>{overallConversionRate}%</div>
              </div>
            </div>

            <div className="card" style={{ padding: '20px', display: 'flex', alignItems: 'center', gap: '16px' }}>
              <div style={{ padding: '12px', background: 'rgba(139, 92, 246, 0.1)', borderRadius: '12px', color: 'var(--accent-purple)' }}>
                <Award size={24} />
              </div>
              <div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Top Converter</div>
                <div style={{ fontSize: '1rem', fontWeight: 700, wordBreak: 'break-all' }}>{bestConvertingEmp}</div>
              </div>
            </div>
          </div>

          {/* Performance Data Table */}
          <div className="card" style={{ padding: '24px', overflowX: 'auto' }}>
            <h2 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '20px' }}>Employee Performance Metrics</h2>
            
            {processedEmployees.length > 0 ? (
              <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border)', color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                    <th style={{ padding: '12px 8px' }}>Employee ID</th>
                    <th style={{ padding: '12px 8px' }}>Shift Start</th>
                    <th style={{ padding: '12px 8px' }}>Shift End</th>
                    <th style={{ padding: '12px 8px' }}>Presence Hours</th>
                    <th style={{ padding: '12px 8px' }}>Break Time</th>
                    <th style={{ padding: '12px 8px' }}>Idle Hours</th>
                    <th style={{ padding: '12px 8px', textAlign: 'center' }}>Customers Served</th>
                    <th style={{ padding: '12px 8px', textAlign: 'center' }}>Avg Service Time</th>
                    <th style={{ padding: '12px 8px', textAlign: 'right' }}>Conversion Rate</th>
                  </tr>
                </thead>
                <tbody>
                  {processedEmployees.map((emp) => (
                    <tr key={emp.id} className="table-row" style={{ borderBottom: '1px solid rgba(255,255,255,0.03)', fontSize: '0.9rem' }}>
                      <td style={{ padding: '16px 8px', fontWeight: 600, color: 'var(--text-primary)' }}>{emp.id}</td>
                      <td style={{ padding: '16px 8px' }}>{emp.login}</td>
                      <td style={{ padding: '16px 8px' }}>{emp.logout}</td>
                      <td style={{ padding: '16px 8px' }}>{emp.presence}</td>
                      <td style={{ padding: '16px 8px', color: 'var(--accent-amber)' }}>{emp.breakTime}</td>
                      <td style={{ padding: '16px 8px', color: 'var(--text-muted)' }}>{emp.idleTime}</td>
                      <td style={{ padding: '16px 8px', textAlign: 'center', fontWeight: 600 }}>{emp.customersServed}</td>
                      <td style={{ padding: '16px 8px', textAlign: 'center' }}>{emp.avgInteraction}</td>
                      <td style={{ padding: '16px 8px', textAlign: 'right', fontWeight: 700, color: 'var(--accent-emerald)' }}>{emp.conversion}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div style={{ textAlign: 'center', padding: '60px 0', color: 'var(--text-muted)' }}>
                No active employee shifts recorded for this date.
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default Analytics;

