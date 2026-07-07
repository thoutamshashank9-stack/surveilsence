import React from 'react';
import { Routes, Route } from 'react-router-dom';
import Sidebar from './components/layout/Sidebar';
import Header from './components/layout/Header';
import Dashboard from './pages/Dashboard';
import LiveView from './pages/LiveView';
import Alerts from './pages/Alerts';
import Analytics from './pages/Analytics';
import Settings from './pages/Settings';

export const App: React.FC = () => {
  return (
    <div className="app-layout">
      {/* Sidebar navigation */}
      <Sidebar />

      {/* Main panel */}
      <main className="main-content">
        <Header />
        
        {/* Router switches */}
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/live" element={<LiveView />} />
          <Route path="/alerts" element={<Alerts />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </main>
    </div>
  );
};
export default App;
