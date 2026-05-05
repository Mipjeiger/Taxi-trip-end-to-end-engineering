import React from "react";
import { useMobile } from "../hooks/useMobile";

interface MobileLayoutProps {
    children: React.ReactNode;
    showHeader?: boolean;
    title?: string;
}

export const MobileLayout: React.FC<MobileLayoutProps> = ({ 
    children, 
    showHeader = true, 
    title, 
}) => {
    const { isMobile, safeAreaInsets } = useMobile();

    if (!isMobile) {
        return <>{children}</>
    }

    return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100vh',
        background: '#f5f5f5',
        paddingTop: `${safeAreaInsets.top}px`,
        paddingBottom: `${safeAreaInsets.bottom}px`,
        paddingLeft: `${safeAreaInsets.left}px`,
        paddingRight: `${safeAreaInsets.right}px`,
      }}
    >
      {showHeader && (
        <div
          style={{
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            color: '#fff',
            padding: '16px 20px',
            textAlign: 'center',
            boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
          }}
        >
          <h1 style={{ margin: 0, fontSize: '1.3em', fontWeight: 'bold' }}>
            {title || '🚗 Taxi Trip'}
          </h1>
        </div>
      )}

      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          overflowX: 'hidden',
          WebkitOverflowScrolling: 'touch',
        }}
      >
        {children}
      </div>
    </div>
  );
};