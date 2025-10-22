import { Routes, Route, Navigate } from 'react-router-dom'
import { useState, useEffect } from 'react'
import Layout from './components/Layout'
import Login from './pages/Login'
import Queue from './pages/Queue'
import Investigator from './pages/Investigator'
import LiveOps from './pages/LiveOps'
import Policy from './pages/Policy'
import { AuthProvider, useAuth } from './contexts/AuthContext'

function ProtectedRoute({ children }) {
  const { isAuthenticated, loading } = useAuth()
  
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-primary-600"></div>
      </div>
    )
  }
  
  return isAuthenticated ? children : <Navigate to="/login" />
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/" element={
        <ProtectedRoute>
          <Layout />
        </ProtectedRoute>
      }>
        <Route index element={<Navigate to="/queue" />} />
        <Route path="queue" element={<Queue />} />
        <Route path="investigator/:caseId" element={<Investigator />} />
        <Route path="live-ops" element={<LiveOps />} />
        <Route path="policy" element={<Policy />} />
      </Route>
    </Routes>
  )
}

function App() {
  return (
    <AuthProvider>
      <AppRoutes />
    </AuthProvider>
  )
}

export default App
