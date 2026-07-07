import React from 'react';
import { Loader2 } from 'lucide-react';

export const LoadingSpinner: React.FC = () => {
  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      gap: '12px',
      padding: '40px',
      color: 'var(--text-secondary)'
    }}>
      <Loader2 size={32} style={{ animation: 'spin 1.5s linear infinite' }} />
      <span style={{ fontSize: '0.85rem' }}>Loading data streams...</span>
      
      <style>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};
export default LoadingSpinner;
