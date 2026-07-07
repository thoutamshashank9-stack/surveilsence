import { create } from 'zustand';
import { Alert } from '../types';

interface AlertState {
  alerts: Alert[];
  unreadCount: number;
  setAlerts: (alerts: Alert[]) => void;
  addAlert: (alert: Alert) => void;
  acknowledgeAlert: (alertId: number, acknowledgedAlert: Alert) => void;
}

export const useAlertStore = create<AlertState>((set) => ({
  alerts: [],
  unreadCount: 0,
  setAlerts: (alerts) => set({
    alerts,
    unreadCount: alerts.filter((a) => a.status === 'active').length
  }),
  addAlert: (alert) => set((state) => {
    // Prevent duplicate alert keys
    if (state.alerts.some((a) => a.id === alert.id)) return state;
    const updatedAlerts = [alert, ...state.alerts].slice(0, 100); // Keep last 100
    return {
      alerts: updatedAlerts,
      unreadCount: state.unreadCount + (alert.status === 'active' ? 1 : 0)
    };
  }),
  acknowledgeAlert: (alertId, acknowledgedAlert) => set((state) => ({
    alerts: state.alerts.map((a) => a.id === alertId ? acknowledgedAlert : a),
    unreadCount: Math.max(0, state.unreadCount - 1)
  }))
}));
export default useAlertStore;
