import React from 'react';
import { LucideIcon } from 'lucide-react';

interface KPICardProps {
  title: string;
  value: string | number;
  change?: string;
  isPositive?: boolean;
  icon: LucideIcon;
  colorClass: 'blue' | 'emerald' | 'amber' | 'purple';
}

export const KPICard: React.FC<KPICardProps> = ({
  title,
  value,
  change,
  isPositive = true,
  icon: Icon,
  colorClass
}) => {
  const getIconColor = () => {
    switch (colorClass) {
      case 'blue': return 'var(--accent-blue)';
      case 'emerald': return 'var(--accent-emerald)';
      case 'amber': return 'var(--accent-amber)';
      case 'purple': return 'var(--accent-purple)';
    }
  };

  return (
    <div className={`card kpi-card ${colorClass} slide-up`}>
      <div className="kpi-card-header">
        <span>{title}</span>
        <Icon size={18} style={{ color: getIconColor() }} />
      </div>
      
      <div className="kpi-value">{value}</div>
      
      {change && (
        <div className={`kpi-change ${isPositive ? 'positive' : 'negative'}`}>
          <span>{isPositive ? '▲' : '▼'}</span>
          <span>{change}</span>
          <span style={{ color: 'var(--text-muted)', marginLeft: '4px' }}>vs yesterday</span>
        </div>
      )}
    </div>
  );
};
export default KPICard;
