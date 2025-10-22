import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { 
  Activity, 
  TrendingUp, 
  Clock, 
  Shield, 
  AlertTriangle,
  CheckCircle,
  XCircle,
  BarChart3
} from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, PieChart, Pie, Cell } from 'recharts'
import { api, endpoints } from '../services/api'

const COLORS = ['#3b82f6', '#ef4444', '#f59e0b', '#10b981']

export default function LiveOps() {
  const [timeRange, setTimeRange] = useState('1h')
  const [metrics, setMetrics] = useState({
    decisionsPerSecond: 0,
    allowRate: 0,
    holdRate: 0,
    blockRate: 0,
    avgLatency: 0
  })

  // Mock data for demonstration
  const mockDecisionsData = [
    { time: '10:00', allow: 45, hold: 12, block: 3 },
    { time: '10:01', allow: 52, hold: 8, block: 5 },
    { time: '10:02', allow: 38, hold: 15, block: 2 },
    { time: '10:03', allow: 61, hold: 6, block: 4 },
    { time: '10:04', allow: 47, hold: 11, block: 3 },
    { time: '10:05', allow: 55, hold: 9, block: 2 },
  ]

  const mockLatencyData = [
    { time: '10:00', p50: 120, p95: 180 },
    { time: '10:01', p50: 115, p95: 175 },
    { time: '10:02', p50: 125, p95: 185 },
    { time: '10:03', p50: 110, p95: 170 },
    { time: '10:04', p50: 130, p95: 190 },
    { time: '10:05', p50: 118, p95: 178 },
  ]

  const mockModelPerformance = [
    { name: 'XGBoost', accuracy: 0.92, latency: 45 },
    { name: 'Neural Network', accuracy: 0.89, latency: 78 },
    { name: 'Rules Engine', accuracy: 0.85, latency: 12 },
  ]

  const mockDecisionDistribution = [
    { name: 'Allow', value: 65, color: '#10b981' },
    { name: 'Hold', value: 25, color: '#f59e0b' },
    { name: 'Block', value: 10, color: '#ef4444' },
  ]

  // Simulate real-time updates
  useEffect(() => {
    const interval = setInterval(() => {
      setMetrics(prev => ({
        decisionsPerSecond: Math.floor(Math.random() * 20) + 10,
        allowRate: Math.floor(Math.random() * 20) + 60,
        holdRate: Math.floor(Math.random() * 15) + 20,
        blockRate: Math.floor(Math.random() * 10) + 5,
        avgLatency: Math.floor(Math.random() * 50) + 100
      }))
    }, 2000)

    return () => clearInterval(interval)
  }, [])

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Live Operations</h1>
          <p className="mt-1 text-sm text-gray-500">
            Real-time fraud detection monitoring and metrics
          </p>
        </div>
        <div className="flex items-center space-x-4">
          <select
            className="input w-32"
            value={timeRange}
            onChange={(e) => setTimeRange(e.target.value)}
          >
            <option value="1h">Last Hour</option>
            <option value="24h">Last 24h</option>
            <option value="7d">Last 7 days</option>
          </select>
          <div className="flex items-center space-x-2">
            <div className="w-2 h-2 bg-success-500 rounded-full animate-pulse"></div>
            <span className="text-sm text-gray-600">Live</span>
          </div>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
        <div className="card p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <Activity className="h-8 w-8 text-primary-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500">Decisions/sec</p>
              <p className="text-2xl font-semibold text-gray-900">{metrics.decisionsPerSecond}</p>
            </div>
          </div>
        </div>

        <div className="card p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <CheckCircle className="h-8 w-8 text-success-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500">Allow Rate</p>
              <p className="text-2xl font-semibold text-gray-900">{metrics.allowRate}%</p>
            </div>
          </div>
        </div>

        <div className="card p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <AlertTriangle className="h-8 w-8 text-warning-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500">Hold Rate</p>
              <p className="text-2xl font-semibold text-gray-900">{metrics.holdRate}%</p>
            </div>
          </div>
        </div>

        <div className="card p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <XCircle className="h-8 w-8 text-danger-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500">Block Rate</p>
              <p className="text-2xl font-semibold text-gray-900">{metrics.blockRate}%</p>
            </div>
          </div>
        </div>

        <div className="card p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <Clock className="h-8 w-8 text-blue-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500">Avg Latency</p>
              <p className="text-2xl font-semibold text-gray-900">{metrics.avgLatency}ms</p>
            </div>
          </div>
        </div>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Decision Trends */}
        <div className="card p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Decision Trends</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={mockDecisionsData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="time" />
              <YAxis />
              <Tooltip />
              <Line type="monotone" dataKey="allow" stroke="#10b981" strokeWidth={2} name="Allow" />
              <Line type="monotone" dataKey="hold" stroke="#f59e0b" strokeWidth={2} name="Hold" />
              <Line type="monotone" dataKey="block" stroke="#ef4444" strokeWidth={2} name="Block" />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Latency Trends */}
        <div className="card p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Latency Trends</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={mockLatencyData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="time" />
              <YAxis />
              <Tooltip />
              <Line type="monotone" dataKey="p50" stroke="#3b82f6" strokeWidth={2} name="P50" />
              <Line type="monotone" dataKey="p95" stroke="#ef4444" strokeWidth={2} name="P95" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Model Performance */}
        <div className="card p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Model Performance</h3>
          <div className="space-y-4">
            {mockModelPerformance.map((model) => (
              <div key={model.name} className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <Shield className="h-5 w-5 text-gray-400" />
                  <span className="text-sm font-medium text-gray-900">{model.name}</span>
                </div>
                <div className="flex items-center space-x-4">
                  <div className="text-right">
                    <div className="text-sm font-medium text-gray-900">
                      {(model.accuracy * 100).toFixed(1)}%
                    </div>
                    <div className="text-xs text-gray-500">Accuracy</div>
                  </div>
                  <div className="text-right">
                    <div className="text-sm font-medium text-gray-900">
                      {model.latency}ms
                    </div>
                    <div className="text-xs text-gray-500">Latency</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Decision Distribution */}
        <div className="card p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Decision Distribution</h3>
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie
                data={mockDecisionDistribution}
                cx="50%"
                cy="50%"
                innerRadius={40}
                outerRadius={80}
                paddingAngle={5}
                dataKey="value"
              >
                {mockDecisionDistribution.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
          <div className="flex justify-center space-x-6 mt-4">
            {mockDecisionDistribution.map((item) => (
              <div key={item.name} className="flex items-center space-x-2">
                <div 
                  className="w-3 h-3 rounded-full" 
                  style={{ backgroundColor: item.color }}
                ></div>
                <span className="text-sm text-gray-600">{item.name} ({item.value}%)</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Recent Decisions */}
      <div className="card p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Recent Decisions</h3>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Event ID
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Risk Score
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Decision
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Latency
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Timestamp
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {Array.from({ length: 10 }, (_, i) => (
                <tr key={i} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-gray-900">
                    {`evt_${Math.random().toString(36).substr(2, 8)}`}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {(Math.random() * 100).toFixed(1)}%
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`badge ${
                      Math.random() > 0.7 ? 'badge-danger' : 
                      Math.random() > 0.4 ? 'badge-warning' : 'badge-success'
                    }`}>
                      {Math.random() > 0.7 ? 'Block' : Math.random() > 0.4 ? 'Hold' : 'Allow'}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {Math.floor(Math.random() * 100 + 50)}ms
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {new Date(Date.now() - Math.random() * 3600000).toLocaleTimeString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
