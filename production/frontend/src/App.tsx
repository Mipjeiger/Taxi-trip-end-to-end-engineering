import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Home } from './pages/Home';
import { RideBooking } from './pages/RideBooking';
import { DriverDashboard } from './pages/DriverDashboard';
import { Dashboard } from './pages/Dashboard';
import { RideHistory } from './pages/RideHistory';
import { AIChat } from './pages/AIChat';
import { Profile } from './pages/Profile';
import { Notifications } from './pages/Notifications';
import { AdminFleet } from './pages/AdminFleet';
import { DriverTracking } from './pages/DriverTracking';
import { AppLayout } from './layouts/AppLayout';

function App() {
  return (
    <BrowserRouter>
      <AppLayout>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/booking" element={<RideBooking />} />
          <Route path="/tracking" element={<DriverTracking />} />
          <Route path="/history" element={<RideHistory />} />
          <Route path="/driver" element={<DriverDashboard />} />
          <Route path="/analytics" element={<Dashboard />} />
          <Route path="/chat" element={<AIChat />} />
          <Route path="/profile" element={<Profile />} />
          <Route path="/notifications" element={<Notifications />} />
          <Route path="/admin" element={<AdminFleet />} />
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </AppLayout>
    </BrowserRouter>
  );
}

export default App;