import React from 'react';
import { Button } from '../components/UI/Button';
import { RouteMap } from '../components/Map/RouteMap';

export const Home: React.FC = () => {
  
    return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <h1 style={styles.title}>🚗 Gojek</h1>
        <p style={styles.subtitle}>ML-Powered Ride Sharing Platform</p>
      </div>

      {/* Main Content */}
      <div style={styles.content}>
        {/* Quick Stats */}
        <div style={styles.statsGrid}>
          <div style={styles.statCard}>
            <div style={styles.statNumber}>2,847</div>
            <div style={styles.statLabel}>Active Rides</div>
          </div>
          <div style={styles.statCard}>
            <div style={styles.statNumber}>4.8★</div>
            <div style={styles.statLabel}>Avg Rating</div>
          </div>
          <div style={styles.statCard}>
            <div style={styles.statNumber}>98%</div>
            <div style={styles.statLabel}>On-Time</div>
          </div>
        </div>

        {/* Action Buttons */}
        <div style={styles.buttonGrid}>
          <Link to="/booking" style={{ textDecoration: 'none' }}>
            <button style={styles.primaryButton}>
              📍 Book a Ride
            </button>
          </Link>
          <Link to="/driver" style={{ textDecoration: 'none' }}>
            <button style={styles.secondaryButton}>
              🚗 Driver Dashboard
            </button>
          </Link>
          <Link to="/analytics" style={{ textDecoration: 'none' }}>
            <button style={styles.secondaryButton}>
              📊 Analytics
            </button>
          </Link>
        </div>

        {/* Features */}
        <div style={styles.features}>
          <h2 style={styles.featuresTitle}>Features</h2>
          <div style={styles.featureGrid}>
            <div style={styles.featureItem}>
              <div style={styles.featureIcon}>🤖</div>
              <h3>ML Predictions</h3>
              <p>Smart route & price optimization</p>
            </div>
            <div style={styles.featureItem}>
              <div style={styles.featureIcon}>💰</div>
              <h3>Dynamic Pricing</h3>
              <p>Fair prices based on demand</p>
            </div>
            <div style={styles.featureItem}>
              <div style={styles.featureIcon}>📍</div>
              <h3>Real-time Tracking</h3>
              <p>Live ride tracking & updates</p>
            </div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer style={styles.footer}>
        <p>© 2026 Gojek. All rights reserved.</p>
      </footer>
    </div>
  );
};

const styles: { [key: string]: React.CSSProperties } = {
  container: {
    minHeight: '100vh',
    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    color: '#fff',
    fontFamily: 'system-ui, -apple-system, sans-serif',
  },
  header: {
    textAlign: 'center',
    padding: '60px 20px 40px',
  },
  title: {
    fontSize: '3.5em',
    margin: '0 0 10px',
    fontWeight: 'bold',
  },
  subtitle: {
    fontSize: '1.2em',
    margin: 0,
    opacity: 0.9,
  },
  content: {
    maxWidth: '1200px',
    margin: '0 auto',
    padding: '40px 20px',
  },
  statsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
    gap: '20px',
    marginBottom: '40px',
  },
  statCard: {
    background: 'rgba(255,255,255,0.1)',
    backdropFilter: 'blur(10px)',
    padding: '30px',
    borderRadius: '12px',
    textAlign: 'center',
    border: '1px solid rgba(255,255,255,0.2)',
  },
  statNumber: {
    fontSize: '2em',
    fontWeight: 'bold',
    marginBottom: '10px',
  },
  statLabel: {
    fontSize: '0.9em',
    opacity: 0.9,
  },
  buttonGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
    gap: '20px',
    marginBottom: '60px',
  },
  primaryButton: {
    padding: '16px 32px',
    fontSize: '1.1em',
    background: '#fff',
    color: '#667eea',
    border: 'none',
    borderRadius: '8px',
    cursor: 'pointer',
    fontWeight: 'bold',
    transition: 'all 0.3s ease',
    boxShadow: '0 4px 15px rgba(0,0,0,0.2)',
  },
  secondaryButton: {
    padding: '16px 32px',
    fontSize: '1.1em',
    background: 'rgba(255,255,255,0.2)',
    color: '#fff',
    border: '2px solid #fff',
    borderRadius: '8px',
    cursor: 'pointer',
    fontWeight: 'bold',
    transition: 'all 0.3s ease',
  },
  features: {
    marginTop: '60px',
  },
  featuresTitle: {
    fontSize: '2em',
    textAlign: 'center',
    marginBottom: '40px',
  },
  featureGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
    gap: '30px',
  },
  featureItem: {
    background: 'rgba(255,255,255,0.1)',
    backdropFilter: 'blur(10px)',
    padding: '30px',
    borderRadius: '12px',
    textAlign: 'center',
    border: '1px solid rgba(255,255,255,0.2)',
  },
  featureIcon: {
    fontSize: '3em',
    marginBottom: '15px',
  },
  footer: {
    textAlign: 'center',
    padding: '30px',
    borderTop: '1px solid rgba(255,255,255,0.1)',
    marginTop: '60px',
    opacity: 0.8,
  },
};