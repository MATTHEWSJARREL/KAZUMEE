import { useState, useEffect, useCallback } from 'react';
import { useApi, apiClient } from './useApi';

export interface MonitoringStats {
  clip_pipeline: {
    total_events: number;
    success_count: number;
    error_count: number;
    success_rate: number;
    last_event: any;
  };
  storage: {
    total_files: number;
    total_size_bytes: number;
    total_size_mb: number;
    extracted_files: number;
    approved_files: number;
    exported_files: number;
  };
  timestamp: string;
}

export interface MonitoringEvent {
  timestamp: string;
  type: string;
  streamer_id: string;
  clip_id?: number;
  message: string;
  duration_ms?: number;
  error?: string;
  metadata?: Record<string, any>;
}

export interface MonitoringData {
  stats: MonitoringStats | null;
  events: MonitoringEvent[];
  errors: MonitoringEvent[];
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

export function useMonitoring(interval: number = 5000): MonitoringData {
  const [stats, setStats] = useState<MonitoringStats | null>(null);
  const [events, setEvents] = useState<MonitoringEvent[]>([]);
  const [errors, setErrors] = useState<MonitoringEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchMonitoringData = useCallback(async () => {
    try {
      setError(null);
      const token = localStorage.getItem('authToken');

      const [statsData, eventsData, errorsData] = await Promise.all([
        fetch('/api/monitoring/stats', {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        }).then(r => r.json()),
        fetch('/api/monitoring/events?limit=50', {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        }).then(r => r.json()),
        fetch('/api/monitoring/errors?limit=20', {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        }).then(r => r.json()),
      ]);

      setStats(statsData);
      setEvents(eventsData.events || []);
      setErrors(errorsData.errors || []);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch monitoring data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchMonitoringData();
    const intervalId = setInterval(fetchMonitoringData, interval);
    return () => clearInterval(intervalId);
  }, [fetchMonitoringData, interval]);

  return { stats, events, errors, loading, error, refresh: fetchMonitoringData };
}

export async function getHealthStatus(): Promise<{ status: string; timestamp: string }> {
  try {
    const response = await fetch('/api/monitoring/health');
    return await response.json();
  } catch {
    return { status: 'unhealthy', timestamp: new Date().toISOString() };
  }
}

export async function getClipSuccessRate(token: string) {
  const response = await fetch('/api/monitoring/clip-success-rate', {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  });
  if (!response.ok) throw new Error('Failed to fetch success rate');
  return await response.json();
}

export async function getExtractionFailures(token: string, limit: number = 20) {
  const response = await fetch(`/api/monitoring/extraction-failures?limit=${limit}`, {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  });
  if (!response.ok) throw new Error('Failed to fetch failures');
  return await response.json();
}

export async function getLogFiles(token: string) {
  const response = await fetch('/api/monitoring/log-files', {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  });
  if (!response.ok) throw new Error('Failed to fetch log files');
  return await response.json();
}
