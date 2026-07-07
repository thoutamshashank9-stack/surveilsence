import React, { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { Clock } from 'lucide-react';
import { useWebSocket } from '../../hooks/useWebSocket';

export const Header: React.FC = () => {
  const location = useLocation();
  const { connected } = useWebSocket();
  const [timeStr, setTimeStr] = useState<string>('');

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setTimeStr(now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }));
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  const getPageTitle = () => {
    switch (location.pathname) {
      case '/': return 'Dashboard Overview';
      case '/live': return 'Live Monitor Grid';
      case '/alerts': return 'Security Alerts Feed';
      case '/analytics': return 'Business Intelligence Trends';
      case '/settings': return 'Platform Configurations';
      default: return 'Edge AI CCTV Platform';
    }
  };

  return (
    <header className="header">
      {/* Title */}
      <h1 style={{ fontSize: '1.25rem', fontWeight: 600 }}>{getPageTitle()}</h1>

      {/* Clock & Status */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
        {/* Clock */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
          <Clock size={16} />
          <span>{timeStr}</span>
        </div>

        {/* Network status */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.85rem' }}>
          <span className={`status-dot ${connected ? 'online' : 'offline'}`}></span>
          <span style={{ color: connected ? 'var(--text-primary)' : 'var(--text-muted)' }}>
            {connected ? 'Edge Pipeline' : 'Reconnecting'}
          </span>
        </div>
      </div>
    </header>
  );
};
export default Header;
