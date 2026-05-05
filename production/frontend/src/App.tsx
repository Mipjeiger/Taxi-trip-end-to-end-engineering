import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Home } from './pages/Home';
import { RideBooking } from './pages/RideBooking';
import { DriverDashboard } from './pages/DriverDashboard';
import { Dashboard } from './pages/Dashboard';
import { MobileNav } from './components/MobileNav';
import { MobileLayout } from './layouts/MobileLayout';
import { useMobile } from './hooks/useMobile';

function App() {
  const { isMobile } = useMobile();

  return (
    <BrowserRouter>
      <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
        {isMobile ? (
          <>
            <MobileLayout>
              <Routes>
                <Route path="/" element={<Home />} />
                <Route path="/booking" element={<RideBooking />} />
                <Route path="/driver" element={<DriverDashboard />} />
                <Route path="/analytics" element={<Dashboard />} />
                <Route path="*" element={<Navigate to="/" />} />
              </Routes>
            </MobileLayout>
            <MobileNav />
          </>
        ) : (
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/booking" element={<RideBooking />} />
            <Route path="/driver" element={<DriverDashboard />} />
            <Route path="/analytics" element={<Dashboard />} />
            <Route path="*" element={<Navigate to="/" />} />
          </Routes>
        )}
      </div>
    </BrowserRouter>
  );
}

export default App;