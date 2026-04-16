import { useState, useEffect } from 'react';
import { CONFIG } from '../constants/Config';

export interface FleetNode {
  node_id: string;
  status: 'online' | 'offline' | 'degraded';
  last_heartbeat: number;
  ip_address: string;
  drift_score: number;
  details?: any;
}

export function useFleet() {
  const [nodes, setNodes] = useState<FleetNode[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchFleet = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${CONFIG.API_BASE_URL}/fleet/status`);
      if (!response.ok) {
        throw new Error('Failed to fetch fleet status');
      }
      const data = await response.json();
      setNodes(data);
      setError(null);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchFleet();
    
    // Auto-refresh every 30 seconds
    const interval = setInterval(fetchFleet, 30000);
    return () => clearInterval(interval);
  }, []);

  return { nodes, loading, error, refresh: fetchFleet };
}
