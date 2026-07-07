import React from 'react';
import { NavLink } from 'react-router-dom';
import { ShieldAlert, Video, LayoutDashboard, LineChart, Settings, Radio } from 'lucide-react';
import useAlertStore from '../../store/alertStore';

export const Sidebar: React.FC = () => {
  const unreadCount = useAlertStore((state) => state.unreadCount);

  return (
    <aside className="sidebar">
      {/* Brand logo */}
      <div style={{
        padding: '24px',
        borderBottom: '1px solid var(--border)',
        display: 'flex',
        alignItems: 'center',
        gap: '12px',
        fontWeight: 'bold',
        fontSize: '1.1rem',
        letterSpacing: '0.5px'
      }}>
        <ShieldAlert size={24} style={{ color: 'var(--accent-blue)', filter: 'drop-shadow(var(--glow-blue))' }} />
        <span>SURVEILSENCE</span>
      </div>

      {/* Nav Menu */}
      <nav style={{ flexGrow: 1, padding: '16px 0', display: 'flex', flexDirection: 'column', gap: '4px' }}>
        <NavLink 
          to="/" 
          className={({ isActive }) => `btn ${isActive ? 'btn-primary' : 'btn-ghost'}`}
          style={{ justifyContent: 'flex-start', margin: '0 16px', textDecoration: 'none' }}
        >
          <LayoutDashboard size={18} />
          <span>Dashboard</span>
        </NavLink>

        <NavLink 
          to="/live" 
          className={({ isActive }) => `btn ${isActive ? 'btn-primary' : 'btn-ghost'}`}
          style={{ justifyContent: 'flex-start', margin: '0 16px', textDecoration: 'none' }}
        >
          <Video size={18} />
          <span>Live Video</span>
        </NavLink>

        <NavLink 
          to="/alerts" 
          className={({ isActive }) => `btn ${isActive ? 'btn-primary' : 'btn-ghost'}`}
          style={{ justifyContent: 'flex-start', margin: '0 16px', position: 'relative', textDecoration: 'none' }}
        >
          <ShieldAlert size={18} />
          <span>Alerts Feed</span>
          {unreadCount > 0 && (
            <span style={{
              position: 'absolute',
              right: '16px',
              background: 'var(--accent-red)',
              color: 'white',
              fontSize: '0.7rem',
              fontWeight: 'bold',
              borderRadius: '99px',
              padding: '2px 6px'
            }}>
              {unreadCount}
            </span>
          )}
        </NavLink>

        <NavLink 
          to="/analytics" 
          className={({ isActive }) => `btn ${isActive ? 'btn-primary' : 'btn-ghost'}`}
          style={{ justifyContent: 'flex-start', margin: '0 16px', textDecoration: 'none' }}
        >
          <LineChart size={18} />
          <span>Analytics</span>
        </NavLink>

        <NavLink 
          to="/settings" 
          className={({ isActive }) => `btn ${isActive ? 'btn-primary' : 'btn-ghost'}`}
          style={{ justifyContent: 'flex-start', margin: '0 16px', textDecoration: 'none' }}
        >
          <Settings size={18} />
          <span>Settings</span>
        </NavLink>
      </nav>

      {/* Footer Uptime status */}
      <div style={{
        padding: '16px 24px',
        borderTop: '1px solid var(--border)',
        fontSize: '0.8rem',
        color: 'var(--text-secondary)',
        display: 'flex',
        alignItems: 'center',
        gap: '8px'
      }}>
        <Radio size={14} style={{ color: 'var(--accent-emerald)', animation: 'pulse 2s infinite' }} />
        <span>System Operations: Online</span>
      </div>
    </aside>
  );
};
export default Sidebar;
