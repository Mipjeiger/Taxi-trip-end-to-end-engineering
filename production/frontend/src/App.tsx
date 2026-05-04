import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Home } from './pages/Home'
import { RideBooking } from './pages/RideBooking';
import { DriverDashboard } from './pages/DriverDashboard';
import { Dashboard } from './pages/Dashboard';

function App() {
    return (
        <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/ride" element={<RideBooking />} />
        <Route path="/driver" element={<DriverDashboard />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/analytics" element={<Dashboard />} />
        <Route path="/booking" element={<Dashboard />} />
        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
    </BrowserRouter>
    );
}

export default App;