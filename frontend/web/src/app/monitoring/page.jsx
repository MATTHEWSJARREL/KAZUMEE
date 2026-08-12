import React, { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { AlertCircle, TrendingUp, Clock, XCircle, CheckCircle } from 'lucide-react';
import { apiFetch, getAuthToken } from '@/lib/apiClient';

export default function MonitoringPage() {
  const [stats, setStats] = useState(null);
  const [events, setEvents] = useState([]);
  const [errors, setErrors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');

  useEffect(() => {
    fetchMonitoringData();
    const interval = setInterval(fetchMonitoringData, 5000); // Refresh every 5 seconds
    return () => clearInterval(interval);
  }, []);

  const fetchMonitoringData = async () => {
    try {
      const [statsRes, eventsRes, errorsRes] = await Promise.all([
        apiFetch('/api/monitoring/stats'),
        apiFetch('/api/monitoring/events?limit=20'),
        apiFetch('/api/monitoring/errors?limit=10'),
      ]);

      if (!statsRes.ok || !eventsRes.ok || !errorsRes.ok) {
        throw new Error('Failed to fetch monitoring data');
      }

      const [statsData, eventsData, errorsData] = await Promise.all([
        statsRes.json(),
        eventsRes.json(),
        errorsRes.json(),
      ]);

      setStats(statsData);
      setEvents(eventsData.events || []);
      setErrors(errorsData.errors || []);
      setError(null);
    } catch (err) {
      console.error('Monitoring fetch error:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="p-6">Loading monitoring data...</div>;
  }

  if (error) {
    return (
      <div className="p-6 bg-red-50 border border-red-200 rounded-lg">
        <AlertCircle className="text-red-600 mb-2" />
        <p className="text-red-700">{error}</p>
      </div>
    );
  }

  const clipStats = stats?.clip_pipeline || {};
  const storageStats = stats?.storage || {};

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">Monitoring Dashboard</h1>
        <p className="text-gray-500 mt-1">Real-time system metrics and events</p>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <MetricCard
          title="Success Rate"
          value={`${clipStats.success_rate || 0}%`}
          icon={<TrendingUp className="text-green-500" />}
          color="green"
        />
        <MetricCard
          title="Total Clips"
          value={clipStats.success_count + clipStats.error_count || 0}
          icon={<CheckCircle className="text-blue-500" />}
          color="blue"
        />
        <MetricCard
          title="Successful"
          value={clipStats.success_count || 0}
          icon={<CheckCircle className="text-green-500" />}
          color="green"
        />
        <MetricCard
          title="Failed"
          value={clipStats.error_count || 0}
          icon={<XCircle className="text-red-500" />}
          color="red"
        />
      </div>

      {/* Storage Stats */}
      <div className="bg-white p-6 rounded-lg shadow">
        <h2 className="text-xl font-bold mb-4">Storage Usage</h2>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <StorageItem label="Total Size" value={`${storageStats.total_size_mb || 0} MB`} />
          <StorageItem label="Total Files" value={storageStats.total_files || 0} />
          <StorageItem label="Extracted" value={storageStats.extracted_files || 0} />
          <StorageItem label="Approved" value={storageStats.approved_files || 0} />
          <StorageItem label="Exported" value={storageStats.exported_files || 0} />
        </div>
      </div>

      {/* Tabs */}
      <div className="bg-white rounded-lg shadow">
        <div className="border-b flex">
          {['overview', 'events', 'errors'].map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-3 font-medium capitalize ${
                activeTab === tab
                  ? 'border-b-2 border-blue-500 text-blue-600'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              {tab === 'overview' ? 'Recent Events' : tab}
            </button>
          ))}
        </div>

        <div className="p-6">
          {activeTab === 'overview' && (
            <div className="space-y-4">
              <div className="flex justify-between items-center mb-4">
                <h3 className="font-bold">Last Event</h3>
                <button
                  onClick={fetchMonitoringData}
                  className="px-3 py-1 bg-blue-100 text-blue-700 rounded text-sm font-medium hover:bg-blue-200"
                >
                  Refresh
                </button>
              </div>
              {clipStats.last_event ? (
                <EventCard event={clipStats.last_event} />
              ) : (
                <p className="text-gray-500">No events recorded yet</p>
              )}
            </div>
          )}

          {activeTab === 'events' && (
            <div className="space-y-3">
              <h3 className="font-bold mb-4">Recent Events (Last 20)</h3>
              {events.length > 0 ? (
                events.map((event, idx) => (
                  <EventCard key={idx} event={event} />
                ))
              ) : (
                <p className="text-gray-500">No events yet</p>
              )}
            </div>
          )}

          {activeTab === 'errors' && (
            <div className="space-y-3">
              <h3 className="font-bold mb-4">Recent Errors (Last 10)</h3>
              {errors.length > 0 ? (
                errors.map((error, idx) => (
                  <div key={idx} className="p-3 bg-red-50 border border-red-200 rounded">
                    <div className="flex items-start gap-3">
                      <AlertCircle className="text-red-600 mt-1 flex-shrink-0" size={16} />
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-red-900">{error.message}</p>
                        {error.error && (
                          <p className="text-sm text-red-700 mt-1 font-mono break-words">
                            {error.error}
                          </p>
                        )}
                        <p className="text-xs text-red-600 mt-2">
                          Clip {error.clip_id || 'N/A'} • {new Date(error.timestamp).toLocaleString()}
                        </p>
                      </div>
                    </div>
                  </div>
                ))
              ) : (
                <p className="text-gray-500">No errors recorded</p>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Event Type Distribution Chart */}
      {events.length > 0 && (
        <div className="bg-white p-6 rounded-lg shadow">
          <h2 className="text-xl font-bold mb-4">Event Distribution</h2>
          <EventDistributionChart events={events} />
        </div>
      )}
    </div>
  );
}

function MetricCard({ title, value, icon, color }) {
  const bgColor = {
    green: 'bg-green-50',
    blue: 'bg-blue-50',
    red: 'bg-red-50',
  }[color];

  return (
    <div className={`${bgColor} p-4 rounded-lg`}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-gray-600 font-medium">{title}</p>
          <p className="text-2xl font-bold mt-1">{value}</p>
        </div>
        <div className="text-2xl">{icon}</div>
      </div>
    </div>
  );
}

function StorageItem({ label, value }) {
  return (
    <div className="p-3 bg-gray-50 rounded">
      <p className="text-xs text-gray-600 font-medium">{label}</p>
      <p className="text-lg font-bold mt-1">{value}</p>
    </div>
  );
}

function EventCard({ event }) {
  const getEventColor = (type) => {
    if (type.includes('success') || type.includes('approved')) return 'bg-green-50 border-green-200';
    if (type.includes('fail') || type.includes('reject') || type.includes('error')) return 'bg-red-50 border-red-200';
    if (type.includes('delete')) return 'bg-yellow-50 border-yellow-200';
    return 'bg-blue-50 border-blue-200';
  };

  const getIcon = (type) => {
    if (type.includes('success') || type.includes('approved')) return <CheckCircle size={16} className="text-green-600" />;
    if (type.includes('fail') || type.includes('reject') || type.includes('error')) return <XCircle size={16} className="text-red-600" />;
    if (type.includes('delete')) return <AlertCircle size={16} className="text-yellow-600" />;
    return <Clock size={16} className="text-blue-600" />;
  };

  return (
    <div className={`p-3 border rounded ${getEventColor(event.type)}`}>
      <div className="flex items-start gap-3">
        {getIcon(event.type)}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-medium text-sm capitalize">{event.type.replace(/_/g, ' ')}</span>
            {event.duration_ms && (
              <span className="text-xs px-2 py-1 bg-gray-200 rounded text-gray-700">
                {event.duration_ms}ms
              </span>
            )}
          </div>
          <p className="text-sm mt-1">{event.message}</p>
          {event.error && (
            <p className="text-xs text-red-600 mt-1 font-mono">Error: {event.error}</p>
          )}
          <p className="text-xs text-gray-500 mt-2">
            {new Date(event.timestamp).toLocaleString()}
          </p>
        </div>
      </div>
    </div>
  );
}

function EventDistributionChart({ events }) {
  const distribution = {};
  events.forEach(e => {
    distribution[e.type] = (distribution[e.type] || 0) + 1;
  });

  const data = Object.entries(distribution).map(([type, count]) => ({
    name: type.replace(/_/g, ' '),
    value: count,
  }));

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={data}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="name" angle={-45} textAnchor="end" height={100} />
        <YAxis />
        <Tooltip />
        <Bar dataKey="value" fill="#3b82f6" />
      </BarChart>
    </ResponsiveContainer>
  );
}
