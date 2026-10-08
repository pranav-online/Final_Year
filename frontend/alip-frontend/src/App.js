import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { AuthProvider, useAuth } from './context/AuthContext';
import Login from './pages/Login';
import Register from './pages/Register';
import FarmerDashboard from './pages/FarmerDashboard';
import DiseaseDetection from './pages/DiseaseDetection';
import WeatherAdvisory from './pages/WeatherAdvisory';
import CropRecommendation from './pages/CropRecommendation';
import BrokerDashboard from './pages/BrokerDashboard';
import DemandAnalysis from './pages/DemandAnalysis';
import CropListing from './pages/CropListing';
import RegionalSupply from './pages/RegionalSupply';
import AllListings from './pages/AllListings';
import Notifications from './pages/Notifications';
import UserProfile from './pages/UserProfile';

function ProtectedRoute({ children, role }) {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" />;
  if (role && user.role !== role) return <Navigate to="/login" />;
  return children;
}

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Toaster position="top-right" />
        <Routes>
          <Route path="/" element={<Navigate to="/login" />} />
          <Route path="/login"    element={<Login />} />
          <Route path="/register" element={<Register />} />

          {/* Farmer Routes */}
          <Route path="/farmer" element={
            <ProtectedRoute role="farmer"><FarmerDashboard /></ProtectedRoute>
          } />
          <Route path="/disease" element={
            <ProtectedRoute role="farmer"><DiseaseDetection /></ProtectedRoute>
          } />
          <Route path="/weather" element={
            <ProtectedRoute role="farmer"><WeatherAdvisory /></ProtectedRoute>
          } />
          <Route path="/crop" element={
            <ProtectedRoute role="farmer"><CropRecommendation /></ProtectedRoute>
          } />

          {/* Shared */}
          <Route path="/listing" element={
            <ProtectedRoute><CropListing /></ProtectedRoute>
          } />

          {/* Broker Routes */}
          <Route path="/broker" element={
            <ProtectedRoute role="broker"><BrokerDashboard /></ProtectedRoute>
          } />
          <Route path="/demand" element={
            <ProtectedRoute role="broker"><DemandAnalysis /></ProtectedRoute>
          } />
          <Route path="/supply" element={
            <ProtectedRoute role="broker"><RegionalSupply /></ProtectedRoute>
          } />
          <Route path="/listings" element={
            <ProtectedRoute role="broker"><AllListings /></ProtectedRoute>
          } />
          <Route path="/notifications" element={
            <ProtectedRoute role="broker"><Notifications /></ProtectedRoute>
          } />
          <Route path="/profile" element={
           <ProtectedRoute>
              <UserProfile />
           </ProtectedRoute>
} />

        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
