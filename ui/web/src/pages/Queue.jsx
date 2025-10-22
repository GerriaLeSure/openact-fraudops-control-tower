import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { 
  Clock, 
  User, 
  AlertTriangle, 
  CheckCircle, 
  XCircle,
  Filter,
  Search,
  Plus
} from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { api, endpoints } from '../services/api'

const statusColors = {
  open: 'bg-warning-100 text-warning-800',
  assigned: 'bg-primary-100 text-primary-800',
  investigating: 'bg-blue-100 text-blue-800',
  resolved: 'bg-success-100 text-success-800',
  closed: 'bg-gray-100 text-gray-800'
}

const priorityColors = {
  low: 'bg-gray-100 text-gray-800',
  medium: 'bg-warning-100 text-warning-800',
  high: 'bg-danger-100 text-danger-800',
  critical: 'bg-red-100 text-red-800'
}

export default function Queue() {
  const [filters, setFilters] = useState({
    status: '',
    assigned_to: '',
    priority: ''
  })
  const [searchTerm, setSearchTerm] = useState('')
  const navigate = useNavigate()

  const { data: cases, isLoading, error, refetch } = useQuery({
    queryKey: ['cases', filters],
    queryFn: async () => {
      const params = new URLSearchParams()
      Object.entries(filters).forEach(([key, value]) => {
        if (value) params.append(key, value)
      })
      
      const response = await api.get(`${endpoints.cases}?${params}`)
      return response.data.cases
    },
    refetchInterval: 30000 // Refresh every 30 seconds
  })

  const handleFilterChange = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }))
  }

  const handleCaseClick = (caseId) => {
    navigate(`/investigator/${caseId}`)
  }

  const getSLAStatus = (slaDeadline) => {
    const now = new Date()
    const deadline = new Date(slaDeadline)
    const timeRemaining = deadline - now
    
    if (timeRemaining < 0) {
      return { status: 'breached', color: 'text-danger-600', icon: XCircle }
    } else if (timeRemaining < 2 * 60 * 60 * 1000) { // Less than 2 hours
      return { status: 'warning', color: 'text-warning-600', icon: AlertTriangle }
    } else {
      return { status: 'ok', color: 'text-success-600', icon: CheckCircle }
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <XCircle className="mx-auto h-12 w-12 text-danger-400" />
        <h3 className="mt-2 text-sm font-medium text-gray-900">Error loading cases</h3>
        <p className="mt-1 text-sm text-gray-500">{error.message}</p>
        <button
          onClick={() => refetch()}
          className="mt-4 btn btn-primary"
        >
          Try again
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Case Queue</h1>
          <p className="mt-1 text-sm text-gray-500">
            Manage and investigate fraud cases
          </p>
        </div>
        <button
          onClick={() => refetch()}
          className="btn btn-primary"
        >
          <Plus className="h-4 w-4 mr-2" />
          Refresh
        </button>
      </div>

      {/* Filters */}
      <div className="card p-4">
        <div className="flex flex-wrap gap-4">
          <div className="flex-1 min-w-64">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search cases..."
                className="input pl-10"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
          </div>
          
          <select
            className="input w-40"
            value={filters.status}
            onChange={(e) => handleFilterChange('status', e.target.value)}
          >
            <option value="">All Status</option>
            <option value="open">Open</option>
            <option value="assigned">Assigned</option>
            <option value="investigating">Investigating</option>
            <option value="resolved">Resolved</option>
            <option value="closed">Closed</option>
          </select>
          
          <select
            className="input w-40"
            value={filters.priority}
            onChange={(e) => handleFilterChange('priority', e.target.value)}
          >
            <option value="">All Priority</option>
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
            <option value="critical">Critical</option>
          </select>
          
          <select
            className="input w-40"
            value={filters.assigned_to}
            onChange={(e) => handleFilterChange('assigned_to', e.target.value)}
          >
            <option value="">All Assignees</option>
            <option value="analyst1">Analyst 1</option>
            <option value="analyst2">Analyst 2</option>
            <option value="supervisor">Supervisor</option>
          </select>
        </div>
      </div>

      {/* Cases Table */}
      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Case ID
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Priority
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Risk Score
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Assigned To
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  SLA
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Created
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {cases?.map((caseItem) => {
                const slaStatus = getSLAStatus(caseItem.sla_deadline)
                const SLAIcon = slaStatus.icon
                
                return (
                  <tr
                    key={caseItem.case_id}
                    className="hover:bg-gray-50 cursor-pointer"
                    onClick={() => handleCaseClick(caseItem.case_id)}
                  >
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-medium text-gray-900">
                        {caseItem.case_id}
                      </div>
                      <div className="text-sm text-gray-500">
                        {caseItem.event_id}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`badge ${statusColors[caseItem.status]}`}>
                        {caseItem.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`badge ${priorityColors[caseItem.priority]}`}>
                        {caseItem.priority}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-900">
                        {(caseItem.risk_score * 100).toFixed(1)}%
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <User className="h-4 w-4 text-gray-400 mr-2" />
                        <span className="text-sm text-gray-900">
                          {caseItem.assigned_to || 'Unassigned'}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <SLAIcon className={`h-4 w-4 mr-2 ${slaStatus.color}`} />
                        <span className={`text-sm ${slaStatus.color}`}>
                          {formatDistanceToNow(new Date(caseItem.sla_deadline), { addSuffix: true })}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {formatDistanceToNow(new Date(caseItem.created_at), { addSuffix: true })}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
        
        {cases?.length === 0 && (
          <div className="text-center py-12">
            <CheckCircle className="mx-auto h-12 w-12 text-gray-400" />
            <h3 className="mt-2 text-sm font-medium text-gray-900">No cases found</h3>
            <p className="mt-1 text-sm text-gray-500">
              No cases match your current filters.
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
