import React, { useState, useEffect } from 'react';
import { API } from '../api/client';

export default function Analytics() {
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [timeRange, setTimeRange] = useState(24);

  useEffect(() => {
    fetchAnalytics();
  }, [timeRange]);

  const fetchAnalytics = async () => {
    try {
      setLoading(true);
      const data = await API.getAnalytics(timeRange);
      setAnalytics(data);
    } catch (error) {
      console.error('Failed to fetch analytics:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div className="p-6">Loading analytics...</div>;
  if (!analytics) return <div className="p-6">No analytics data available</div>;

  return (
    <div className="p-6 space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">Analytics Dashboard</h1>
        <select 
          value={timeRange} 
          onChange={(e) => setTimeRange(Number(e.target.value))}
          className="border rounded px-3 py-2"
        >
          <option value={1}>Last Hour</option>
          <option value={24}>Last 24 Hours</option>
          <option value={168}>Last Week</option>
        </select>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {analytics.kpis.map((kpi, index) => (
          <div key={index} className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">{kpi.name}</p>
                <p className="text-2xl font-bold text-gray-900">
                  {kpi.name.includes('Rate') ? `${kpi.value.toFixed(1)}%` : 
                   kpi.name.includes('Time') ? `${kpi.value.toFixed(1)}h` :
                   kpi.name.includes('Hour') ? kpi.value.toFixed(1) :
                   Math.round(kpi.value)}
                </p>
              </div>
              <div className={`w-3 h-3 rounded-full ${
                kpi.trend === 'up' ? 'bg-green-500' :
                kpi.trend === 'down' ? 'bg-red-500' : 'bg-gray-500'
              }`}></div>
            </div>
            {kpi.change_percent !== null && (
              <p className={`text-sm mt-2 ${
                kpi.change_percent > 0 ? 'text-green-600' : 'text-red-600'
              }`}>
                {kpi.change_percent > 0 ? '+' : ''}{kpi.change_percent.toFixed(1)}% from last period
              </p>
            )}
          </div>
        ))}
      </div>

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Decisions per Minute */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-4">Decisions per Minute</h3>
          <div className="h-64 flex items-center justify-center bg-gray-50 rounded">
            <p className="text-gray-500">Chart: {analytics.decisions_per_minute.length} data points</p>
          </div>
        </div>

        {/* Fraud Rate Trend */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-4">Fraud Rate Trend</h3>
          <div className="h-64 flex items-center justify-center bg-gray-50 rounded">
            <p className="text-gray-500">Chart: {analytics.fraud_rate_trend.length} data points</p>
          </div>
        </div>
      </div>

      {/* Distribution Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Action Distribution */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-4">Action Distribution</h3>
          <div className="space-y-2">
            {analytics.action_distribution.map((action, index) => (
              <div key={index} className="flex justify-between items-center">
                <span className="capitalize">{action.action}</span>
                <div className="flex items-center space-x-2">
                  <div className="w-20 bg-gray-200 rounded-full h-2">
                    <div 
                      className="bg-blue-600 h-2 rounded-full" 
                      style={{ width: `${action.percentage}%` }}
                    ></div>
                  </div>
                  <span className="text-sm text-gray-600">{action.percentage.toFixed(1)}%</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Channel Analytics */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-4">Channel Analytics</h3>
          <div className="space-y-3">
            {analytics.channel_analytics.map((channel, index) => (
              <div key={index} className="border-b pb-2">
                <div className="flex justify-between">
                  <span className="font-medium capitalize">{channel.channel}</span>
                  <span className="text-sm text-gray-600">{channel.fraud_rate.toFixed(1)}% fraud</span>
                </div>
                <div className="text-sm text-gray-500">
                  {channel.total_transactions.toLocaleString()} transactions
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Region Analytics */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-4">Region Analytics</h3>
          <div className="space-y-3">
            {analytics.region_analytics.map((region, index) => (
              <div key={index} className="border-b pb-2">
                <div className="flex justify-between">
                  <span className="font-medium">{region.region}</span>
                  <span className="text-sm text-gray-600">{region.fraud_rate.toFixed(1)}% fraud</span>
                </div>
                <div className="text-sm text-gray-500">
                  ${region.avg_amount.toFixed(0)} avg amount
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-4">Summary Statistics</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="text-center">
            <p className="text-2xl font-bold text-blue-600">{analytics.total_transactions.toLocaleString()}</p>
            <p className="text-sm text-gray-600">Total Transactions</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-red-600">{analytics.total_fraud_detected.toLocaleString()}</p>
            <p className="text-sm text-gray-600">Fraud Detected</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-green-600">{analytics.avg_response_time_ms.toFixed(0)}ms</p>
            <p className="text-sm text-gray-600">Avg Response Time</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-purple-600">{analytics.model_accuracy?.toFixed(1)}%</p>
            <p className="text-sm text-gray-600">Model Accuracy</p>
          </div>
        </div>
      </div>
    </div>
  );
}
