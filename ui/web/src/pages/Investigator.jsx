import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { 
  ArrowLeft, 
  Clock, 
  User, 
  AlertTriangle, 
  CheckCircle,
  MessageSquare,
  Activity,
  FileText,
  Shield,
  TrendingUp
} from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { api, endpoints } from '../services/api'

export default function Investigator() {
  const { caseId } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [newNote, setNewNote] = useState('')
  const [newAction, setNewAction] = useState({ type: '', description: '' })

  const { data: caseData, isLoading, error } = useQuery({
    queryKey: ['case', caseId],
    queryFn: async () => {
      const response = await api.get(endpoints.case(caseId))
      return response.data
    }
  })

  const assignMutation = useMutation({
    mutationFn: async (assignedTo) => {
      await api.patch(endpoints.assignCase(caseId), null, {
        params: { assigned_to: assignedTo }
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['case', caseId])
    }
  })

  const addNoteMutation = useMutation({
    mutationFn: async (noteData) => {
      await api.post(endpoints.addNote(caseId), noteData)
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['case', caseId])
      setNewNote('')
    }
  })

  const addActionMutation = useMutation({
    mutationFn: async (actionData) => {
      await api.post(endpoints.addAction(caseId), actionData)
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['case', caseId])
      setNewAction({ type: '', description: '' })
    }
  })

  const updateStatusMutation = useMutation({
    mutationFn: async (status) => {
      await api.patch(endpoints.updateStatus(caseId), null, {
        params: { status }
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['case', caseId])
    }
  })

  const handleAssign = (assignedTo) => {
    assignMutation.mutate(assignedTo)
  }

  const handleAddNote = () => {
    if (newNote.trim()) {
      addNoteMutation.mutate({ content: newNote, is_internal: false })
    }
  }

  const handleAddAction = () => {
    if (newAction.type && newAction.description) {
      addActionMutation.mutate(newAction)
    }
  }

  const handleStatusChange = (status) => {
    updateStatusMutation.mutate(status)
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  if (error || !caseData) {
    return (
      <div className="text-center py-12">
        <AlertTriangle className="mx-auto h-12 w-12 text-danger-400" />
        <h3 className="mt-2 text-sm font-medium text-gray-900">Case not found</h3>
        <p className="mt-1 text-sm text-gray-500">
          The case you're looking for doesn't exist or you don't have access to it.
        </p>
        <button
          onClick={() => navigate('/queue')}
          className="mt-4 btn btn-primary"
        >
          Back to Queue
        </button>
      </div>
    )
  }

  const riskScore = caseData.risk_score * 100
  const riskColor = riskScore >= 80 ? 'text-danger-600' : riskScore >= 60 ? 'text-warning-600' : 'text-success-600'

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <button
            onClick={() => navigate('/queue')}
            className="p-2 text-gray-400 hover:text-gray-600"
          >
            <ArrowLeft className="h-5 w-5" />
          </button>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{caseData.case_id}</h1>
            <p className="text-sm text-gray-500">
              Event ID: {caseData.event_id}
            </p>
          </div>
        </div>
        <div className="flex items-center space-x-2">
          <span className={`badge ${caseData.status === 'open' ? 'badge-warning' : 
            caseData.status === 'assigned' ? 'badge-info' : 
            caseData.status === 'investigating' ? 'badge-info' : 
            caseData.status === 'resolved' ? 'badge-success' : 'badge-info'}`}>
            {caseData.status}
          </span>
          <span className={`badge ${caseData.priority === 'critical' ? 'badge-danger' : 
            caseData.priority === 'high' ? 'badge-danger' : 
            caseData.priority === 'medium' ? 'badge-warning' : 'badge-info'}`}>
            {caseData.priority}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Case Details */}
          <div className="card p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Case Details</h2>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium text-gray-500">Risk Score</label>
                <div className={`text-2xl font-bold ${riskColor}`}>
                  {riskScore.toFixed(1)}%
                </div>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-500">Decision Action</label>
                <div className="text-lg font-semibold text-gray-900">
                  {caseData.decision_action}
                </div>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-500">Created</label>
                <div className="text-sm text-gray-900">
                  {formatDistanceToNow(new Date(caseData.created_at), { addSuffix: true })}
                </div>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-500">Last Updated</label>
                <div className="text-sm text-gray-900">
                  {formatDistanceToNow(new Date(caseData.updated_at), { addSuffix: true })}
                </div>
              </div>
            </div>
          </div>

          {/* Event Timeline */}
          <div className="card p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Event Timeline</h2>
            <div className="space-y-4">
              <div className="flex items-start space-x-3">
                <div className="flex-shrink-0">
                  <div className="w-2 h-2 bg-primary-600 rounded-full mt-2"></div>
                </div>
                <div className="flex-1">
                  <div className="text-sm font-medium text-gray-900">Transaction Detected</div>
                  <div className="text-sm text-gray-500">
                    High-risk transaction flagged by ML models
                  </div>
                  <div className="text-xs text-gray-400">
                    {formatDistanceToNow(new Date(caseData.created_at), { addSuffix: true })}
                  </div>
                </div>
              </div>
              
              <div className="flex items-start space-x-3">
                <div className="flex-shrink-0">
                  <div className="w-2 h-2 bg-warning-600 rounded-full mt-2"></div>
                </div>
                <div className="flex-1">
                  <div className="text-sm font-medium text-gray-900">Case Created</div>
                  <div className="text-sm text-gray-500">
                    Case automatically created due to high risk score
                  </div>
                  <div className="text-xs text-gray-400">
                    {formatDistanceToNow(new Date(caseData.created_at), { addSuffix: true })}
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Model Scores */}
          <div className="card p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Model Scores</h2>
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-gray-50 p-4 rounded-lg">
                <div className="text-sm font-medium text-gray-500">XGBoost</div>
                <div className="text-2xl font-bold text-gray-900">0.85</div>
              </div>
              <div className="bg-gray-50 p-4 rounded-lg">
                <div className="text-sm font-medium text-gray-500">Neural Network</div>
                <div className="text-2xl font-bold text-gray-900">0.78</div>
              </div>
              <div className="bg-gray-50 p-4 rounded-lg">
                <div className="text-sm font-medium text-gray-500">Rules Engine</div>
                <div className="text-2xl font-bold text-gray-900">0.65</div>
              </div>
              <div className="bg-gray-50 p-4 rounded-lg">
                <div className="text-sm font-medium text-gray-500">Ensemble</div>
                <div className="text-2xl font-bold text-gray-900">0.82</div>
              </div>
            </div>
          </div>

          {/* SHAP Features */}
          <div className="card p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Top Contributing Features</h2>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">Velocity (1h)</span>
                <div className="flex items-center space-x-2">
                  <div className="w-32 bg-gray-200 rounded-full h-2">
                    <div className="bg-danger-600 h-2 rounded-full" style={{ width: '85%' }}></div>
                  </div>
                  <span className="text-sm font-medium text-gray-900">0.31</span>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">IP Risk</span>
                <div className="flex items-center space-x-2">
                  <div className="w-32 bg-gray-200 rounded-full h-2">
                    <div className="bg-warning-600 h-2 rounded-full" style={{ width: '70%' }}></div>
                  </div>
                  <span className="text-sm font-medium text-gray-900">0.22</span>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">Geo Distance</span>
                <div className="flex items-center space-x-2">
                  <div className="w-32 bg-gray-200 rounded-full h-2">
                    <div className="bg-warning-600 h-2 rounded-full" style={{ width: '60%' }}></div>
                  </div>
                  <span className="text-sm font-medium text-gray-900">0.18</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Assignment */}
          <div className="card p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Assignment</h3>
            {caseData.assigned_to ? (
              <div className="flex items-center space-x-2">
                <User className="h-5 w-5 text-gray-400" />
                <span className="text-sm text-gray-900">{caseData.assigned_to}</span>
              </div>
            ) : (
              <div className="space-y-2">
                <p className="text-sm text-gray-500">Unassigned</p>
                <button
                  onClick={() => handleAssign('analyst1')}
                  className="btn btn-primary w-full"
                >
                  Assign to Me
                </button>
              </div>
            )}
          </div>

          {/* SLA */}
          <div className="card p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">SLA Status</h3>
            <div className="flex items-center space-x-2">
              <Clock className="h-5 w-5 text-gray-400" />
              <div>
                <div className="text-sm text-gray-900">
                  {formatDistanceToNow(new Date(caseData.sla_deadline), { addSuffix: true })}
                </div>
                <div className="text-xs text-gray-500">
                  {caseData.priority} priority
                </div>
              </div>
            </div>
          </div>

          {/* Actions */}
          <div className="card p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h3>
            <div className="space-y-2">
              <select
                className="input w-full"
                value={caseData.status}
                onChange={(e) => handleStatusChange(e.target.value)}
              >
                <option value="open">Open</option>
                <option value="assigned">Assigned</option>
                <option value="investigating">Investigating</option>
                <option value="resolved">Resolved</option>
                <option value="closed">Closed</option>
              </select>
            </div>
          </div>

          {/* Add Note */}
          <div className="card p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Add Note</h3>
            <div className="space-y-3">
              <textarea
                className="input w-full h-24 resize-none"
                placeholder="Add a note..."
                value={newNote}
                onChange={(e) => setNewNote(e.target.value)}
              />
              <button
                onClick={handleAddNote}
                disabled={!newNote.trim() || addNoteMutation.isPending}
                className="btn btn-primary w-full"
              >
                {addNoteMutation.isPending ? 'Adding...' : 'Add Note'}
              </button>
            </div>
          </div>

          {/* Add Action */}
          <div className="card p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Add Action</h3>
            <div className="space-y-3">
              <select
                className="input w-full"
                value={newAction.type}
                onChange={(e) => setNewAction(prev => ({ ...prev, type: e.target.value }))}
              >
                <option value="">Select action type</option>
                <option value="contact_customer">Contact Customer</option>
                <option value="verify_identity">Verify Identity</option>
                <option value="check_documents">Check Documents</option>
                <option value="escalate">Escalate</option>
                <option value="other">Other</option>
              </select>
              <textarea
                className="input w-full h-20 resize-none"
                placeholder="Action description..."
                value={newAction.description}
                onChange={(e) => setNewAction(prev => ({ ...prev, description: e.target.value }))}
              />
              <button
                onClick={handleAddAction}
                disabled={!newAction.type || !newAction.description || addActionMutation.isPending}
                className="btn btn-primary w-full"
              >
                {addActionMutation.isPending ? 'Adding...' : 'Add Action'}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Notes and Actions */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Notes */}
        <div className="card p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Notes</h3>
          <div className="space-y-4">
            {caseData.notes?.map((note) => (
              <div key={note.note_id} className="border-l-4 border-primary-200 pl-4">
                <div className="text-sm text-gray-900">{note.content}</div>
                <div className="text-xs text-gray-500 mt-1">
                  {note.author} • {formatDistanceToNow(new Date(note.created_at), { addSuffix: true })}
                </div>
              </div>
            ))}
            {(!caseData.notes || caseData.notes.length === 0) && (
              <p className="text-sm text-gray-500">No notes yet</p>
            )}
          </div>
        </div>

        {/* Actions */}
        <div className="card p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Actions</h3>
          <div className="space-y-4">
            {caseData.actions?.map((action) => (
              <div key={action.action_id} className="border-l-4 border-warning-200 pl-4">
                <div className="text-sm font-medium text-gray-900">{action.action_type}</div>
                <div className="text-sm text-gray-600">{action.description}</div>
                <div className="text-xs text-gray-500 mt-1">
                  {action.performed_by} • {formatDistanceToNow(new Date(action.created_at), { addSuffix: true })}
                </div>
              </div>
            ))}
            {(!caseData.actions || caseData.actions.length === 0) && (
              <p className="text-sm text-gray-500">No actions yet</p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
