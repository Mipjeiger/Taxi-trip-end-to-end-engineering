import React, { useState} from "react";
import './AnalyticsHub.css';

type TabType = 'routes' | 'heatmap' | 'efficiency';

interface Analytics {
    type: TabType;
    title: string;
    icon: string;
    path: string;
    description: string;
}

const analytics: Analytics[] = [
    {
        type: 'routes',
        title: 'Route Map',
        icon: '🗺️',
        path: '/analytics/ride_map.html',
        description: 'View all active routes with pickups and drop-offs'
    },
    {
        type: 'heatmap',
        title: 'Traffic Heatmap',
        icon: '🔥',
        path: '/analytics/heatmap.html',
        description: 'Visualize traffic pickup density and congestion traffic patterns'
    },
    {
        type: 'efficiency',
        title: 'Route Efficiency',
        icon: '⚡',
        path: '/analytics/efficiency.html',
        description: 'Analyze top 20 route efficiency by speed ratio'
    }
];

export const AnalyticsHub: React.FC = () => {
    const [activeTab, setActiveTab] = useState<TabType>('routes');

    const currentAnalytics = analytics.find(a => a.type === activeTab);

    return (
    <div className="analytics-hub">
      {/* Header */}
      <div className="analytics-header">
        <h1>📊 Analytics Dashboard</h1>
        <p>Real-time ride analysis and route optimization</p>
      </div>

      {/* Tab Navigation */}
      <div className="analytics-tabs">
        {analytics.map(a => (
          <button
            key={a.type}
            className={`tab-button ${activeTab === a.type ? 'active' : ''}`}
            onClick={() => setActiveTab(a.type)}
          >
            <span className="tab-icon">{a.icon}</span>
            <span className="tab-text">{a.title}</span>
          </button>
        ))}
      </div>

      {/* Active Tab Content */}
      {currentAnalytics && (
        <div className="analytics-container">
          <div className="analytics-info">
            <h2>{currentAnalytics.icon} {currentAnalytics.title}</h2>
            <p>{currentAnalytics.description}</p>
          </div>
          
          <iframe
            src={currentAnalytics.path}
            title={currentAnalytics.title}
            className="analytics-iframe"
          />
        </div>
      )}
    </div>
  );
};