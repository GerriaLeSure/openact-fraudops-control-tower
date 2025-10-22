import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8080'

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor to handle auth errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// API endpoints
export const endpoints = {
  // Auth
  login: '/auth/login',
  me: '/auth/me',
  
  // Cases
  cases: '/cases',
  case: (id) => `/cases/${id}`,
  assignCase: (id) => `/cases/${id}/assign`,
  addNote: (id) => `/cases/${id}/note`,
  addAction: (id) => `/cases/${id}/action`,
  updateStatus: (id) => `/cases/${id}/status`,
  caseSLA: (id) => `/cases/${id}/sla`,
  
  // Live Ops
  decisions: '/decisions',
  metrics: '/metrics',
  
  // Policy
  policy: '/policy',
  
  // Audit
  audit: (id) => `/audit/${id}`,
  auditEvents: '/audit/events',
}
