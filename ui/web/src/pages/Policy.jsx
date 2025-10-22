import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { 
  Settings, 
  Shield, 
  AlertTriangle, 
  CheckCircle,
  Edit,
  Save,
  X
} from 'lucide-react'
import { api, endpoints } from '../services/api'

export default function Policy() {
  const [editingRule, setEditingRule] = useState(null)
  const [editValues, setEditValues] = useState({})

  const { data: policy, isLoading, error } = useQuery({
    queryKey: ['policy'],
    queryFn: async () => {
      const response = await api.get(endpoints.policy)
      return response.data
    }
  })

  const handleEditRule = (ruleName, ruleConfig) => {
    setEditingRule(ruleName)
    setEditValues(ruleConfig)
  }

  const handleSaveRule = () => {
    // In a real implementation, this would save to the backend
    console.log('Saving rule:', editingRule, editValues)
    setEditingRule(null)
    setEditValues({})
  }

  const handleCancelEdit = () => {
    setEditingRule(null)
    setEditValues({})
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
        <AlertTriangle className="mx-auto h-12 w-12 text-danger-400" />
        <h3 className="mt-2 text-sm font-medium text-gray-900">Error loading policy</h3>
        <p className="mt-1 text-sm text-gray-500">{error.message}</p>
      </div>
    )
  }

  const rules = policy?.config?.rules || {}

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Decision Policy</h1>
          <p className="mt-1 text-sm text-gray-500">
            Configure fraud detection rules and thresholds
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <span className="badge badge-info">Version {policy?.version || 'v1.0'}</span>
          <span className="badge badge-success">Active</span>
        </div>
      </div>

      {/* Policy Overview */}
      <div className="card p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Policy Overview</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-danger-50 p-4 rounded-lg">
            <div className="flex items-center">
              <XCircle className="h-8 w-8 text-danger-600" />
              <div className="ml-3">
                <p className="text-sm font-medium text-danger-800">Block Rules</p>
                <p className="text-2xl font-bold text-danger-900">
                  {rules.block?.conditions?.length || 0}
                </p>
              </div>
            </div>
          </div>
          
          <div className="bg-warning-50 p-4 rounded-lg">
            <div className="flex items-center">
              <AlertTriangle className="h-8 w-8 text-warning-600" />
              <div className="ml-3">
                <p className="text-sm font-medium text-warning-800">Hold Rules</p>
                <p className="text-2xl font-bold text-warning-900">
                  {rules.hold?.conditions?.length || 0}
                </p>
              </div>
            </div>
          </div>
          
          <div className="bg-success-50 p-4 rounded-lg">
            <div className="flex items-center">
              <CheckCircle className="h-8 w-8 text-success-600" />
              <div className="ml-3">
                <p className="text-sm font-medium text-success-800">Allow Rules</p>
                <p className="text-2xl font-bold text-success-900">
                  {rules.allow?.conditions?.length || 0}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Rules Configuration */}
      <div className="space-y-6">
        {/* Block Rules */}
        <div className="card p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900 flex items-center">
              <XCircle className="h-5 w-5 text-danger-600 mr-2" />
              Block Rules
            </h3>
            <span className="badge badge-danger">High Risk</span>
          </div>
          
          <div className="space-y-4">
            {rules.block?.conditions?.map((condition, index) => (
              <div key={index} className="bg-gray-50 p-4 rounded-lg">
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <div className="text-sm font-medium text-gray-900">
                      Condition {index + 1}
                    </div>
                    <div className="text-sm text-gray-600 mt-1">
                      {Object.entries(condition).map(([key, value]) => (
                        <span key={key} className="mr-4">
                          <span className="font-medium">{key}:</span> {JSON.stringify(value)}
                        </span>
                      ))}
                    </div>
                  </div>
                  <button
                    onClick={() => handleEditRule('block', condition)}
                    className="btn btn-secondary"
                  >
                    <Edit className="h-4 w-4" />
                  </button>
                </div>
              </div>
            ))}
            
            {(!rules.block?.conditions || rules.block.conditions.length === 0) && (
              <div className="text-center py-8 text-gray-500">
                No block rules configured
              </div>
            )}
          </div>
        </div>

        {/* Hold Rules */}
        <div className="card p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900 flex items-center">
              <AlertTriangle className="h-5 w-5 text-warning-600 mr-2" />
              Hold Rules
            </h3>
            <span className="badge badge-warning">Medium Risk</span>
          </div>
          
          <div className="space-y-4">
            {rules.hold?.conditions?.map((condition, index) => (
              <div key={index} className="bg-gray-50 p-4 rounded-lg">
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <div className="text-sm font-medium text-gray-900">
                      Condition {index + 1}
                    </div>
                    <div className="text-sm text-gray-600 mt-1">
                      {Object.entries(condition).map(([key, value]) => (
                        <span key={key} className="mr-4">
                          <span className="font-medium">{key}:</span> {JSON.stringify(value)}
                        </span>
                      ))}
                    </div>
                  </div>
                  <button
                    onClick={() => handleEditRule('hold', condition)}
                    className="btn btn-secondary"
                  >
                    <Edit className="h-4 w-4" />
                  </button>
                </div>
              </div>
            ))}
            
            {(!rules.hold?.conditions || rules.hold.conditions.length === 0) && (
              <div className="text-center py-8 text-gray-500">
                No hold rules configured
              </div>
            )}
          </div>
        </div>

        {/* Allow Rules */}
        <div className="card p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900 flex items-center">
              <CheckCircle className="h-5 w-5 text-success-600 mr-2" />
              Allow Rules
            </h3>
            <span className="badge badge-success">Low Risk</span>
          </div>
          
          <div className="space-y-4">
            {rules.allow?.conditions?.map((condition, index) => (
              <div key={index} className="bg-gray-50 p-4 rounded-lg">
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <div className="text-sm font-medium text-gray-900">
                      Condition {index + 1}
                    </div>
                    <div className="text-sm text-gray-600 mt-1">
                      {Object.entries(condition).map(([key, value]) => (
                        <span key={key} className="mr-4">
                          <span className="font-medium">{key}:</span> {JSON.stringify(value)}
                        </span>
                      ))}
                    </div>
                  </div>
                  <button
                    onClick={() => handleEditRule('allow', condition)}
                    className="btn btn-secondary"
                  >
                    <Edit className="h-4 w-4" />
                  </button>
                </div>
              </div>
            ))}
            
            {(!rules.allow?.conditions || rules.allow.conditions.length === 0) && (
              <div className="text-center py-8 text-gray-500">
                No allow rules configured
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Rule Editor Modal */}
      {editingRule && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
          <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
            <div className="mt-3">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-medium text-gray-900">
                  Edit {editingRule} Rule
                </h3>
                <button
                  onClick={handleCancelEdit}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <X className="h-6 w-6" />
                </button>
              </div>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    Risk Score Threshold
                  </label>
                  <input
                    type="number"
                    min="0"
                    max="1"
                    step="0.01"
                    className="input mt-1"
                    placeholder="0.90"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    Watchlist Check
                  </label>
                  <select className="input mt-1">
                    <option value="">Select option</option>
                    <option value="required">Required</option>
                    <option value="optional">Optional</option>
                    <option value="disabled">Disabled</option>
                  </select>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    Velocity Check
                  </label>
                  <select className="input mt-1">
                    <option value="">Select option</option>
                    <option value="strict">Strict</option>
                    <option value="moderate">Moderate</option>
                    <option value="lenient">Lenient</option>
                  </select>
                </div>
              </div>
              
              <div className="flex justify-end space-x-3 mt-6">
                <button
                  onClick={handleCancelEdit}
                  className="btn btn-secondary"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSaveRule}
                  className="btn btn-primary"
                >
                  <Save className="h-4 w-4 mr-2" />
                  Save Changes
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Policy Information */}
      <div className="card p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Policy Information</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="text-sm font-medium text-gray-500">Version</label>
            <div className="text-sm text-gray-900">{policy?.version || 'v1.0'}</div>
          </div>
          <div>
            <label className="text-sm font-medium text-gray-500">Effective Date</label>
            <div className="text-sm text-gray-900">
              {policy?.effective_date ? new Date(policy.effective_date).toLocaleDateString() : 'N/A'}
            </div>
          </div>
          <div>
            <label className="text-sm font-medium text-gray-500">Status</label>
            <div className="text-sm text-gray-900">
              <span className="badge badge-success">Active</span>
            </div>
          </div>
          <div>
            <label className="text-sm font-medium text-gray-500">Last Modified</label>
            <div className="text-sm text-gray-900">
              {new Date().toLocaleDateString()}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
