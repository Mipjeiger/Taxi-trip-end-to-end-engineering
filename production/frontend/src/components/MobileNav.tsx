import React from "react";
import { useLocation, useNavigate } from "react-router-dom";

export const MobileNav: React.FC = () => {
    const location = useLocation();
    const navigate = useNavigate();

    const tabs = [
        { path: '/', icon: '🏠', label: 'Home' },
        { path: '/booking', icon: '📍', label: 'Book' },
        { path: '/driver', icon: '🚗', label: 'Drive' },
        { path: '/analytics', icon: '📊', label: 'Stats' },
    ];

    return (
    <div
      style={{
        position: 'fixed',
        bottom: 0,
        left: 0,
        right: 0,
        background: '#fff',
        borderTop: '1px solid #e0e0e0',
        display: 'grid',
        gridTemplateColumns: 'repeat(4, 1fr)',
        gap: 0,
        boxShadow: '0 -2px 8px rgba(0,0,0,0.1)',
      }}
    >
      {tabs.map((tab) => (
        <button
          key={tab.path}
          onClick={() => navigate(tab.path)}
          style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '12px 8px',
            border: 'none',
            background: location.pathname === tab.path ? '#f0f4ff' : '#fff',
            color: location.pathname === tab.path ? '#667eea' : '#999',
            cursor: 'pointer',
            transition: 'all 0.3s ease',
          }}
        >
          <div style={{ fontSize: '1.5em', marginBottom: '4px' }}>{tab.icon}</div>
          <span style={{ fontSize: '0.75em', fontWeight: '500' }}>{tab.label}</span>
        </button>
      ))}
    </div>
  );
};