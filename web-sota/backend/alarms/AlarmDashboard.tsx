/**
 * Alarm Dashboard Component
 *
 * Comprehensive alarm system monitoring interface integrating Nest Protect
 * and Ring alarm systems with real-time status and event correlation.
 */

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Shield,
  Smoke,
  Bell,
  Battery,
  Wifi,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Clock,
  Settings
} from 'lucide-react';

interface NestProtectDevice {
  id: string;
  name: string;
  location: string;
  batteryLevel: number;
  status: 'online' | 'offline' | 'warning';
  smokeStatus: 'clear' | 'warning' | 'alarm';
  coStatus: 'clear' | 'warning' | 'alarm';
  lastSeen: string;
  lastTest: string;
}

interface RingAlarmDevice {
  id: string;
  name: string;
  type: 'door_sensor' | 'motion_detector' | 'keypad' | 'base_station';
  location: string;
  status: 'open' | 'closed' | 'motion' | 'armed' | 'disarmed';
  batteryLevel?: number;
  lastEvent: string;
}

interface AlarmEvent {
  id: string;
  timestamp: string;
  deviceType: 'nest' | 'ring';
  deviceName: string;
  eventType: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  description: string;
  resolved: boolean;
}

interface AlarmDashboardProps {
  className?: string;
}

export const AlarmDashboard: React.FC<AlarmDashboardProps> = ({ className }) => {
  const [nestDevices, setNestDevices] = useState<NestProtectDevice[]>([]);
  const [ringDevices, setRingDevices] = useState<RingAlarmDevice[]>([]);
  const [recentEvents, setRecentEvents] = useState<AlarmEvent[]>([]);
  const [systemStatus, setSystemStatus] = useState<'all_clear' | 'warning' | 'alarm'>('all_clear');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchAlarmData();
    const interval = setInterval(fetchAlarmData, 30000); // Update every 30 seconds
    return () => clearInterval(interval);
  }, []);

  const fetchAlarmData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Fetch data from all alarm systems
      const [nestResponse, ringResponse, eventsResponse] = await Promise.all([
        fetch('/api/alarms/nest-protect'),
        fetch('/api/alarms/ring'),
        fetch('/api/alarms/events?hours=24')
      ]);

      if (!nestResponse.ok || !ringResponse.ok || !eventsResponse.ok) {
        throw new Error('Failed to fetch alarm data');
      }

      const nestData = await nestResponse.json();
      const ringData = await ringResponse.json();
      const eventsData = await eventsResponse.json();

      setNestDevices(nestData.devices || []);
      setRingDevices(ringData.devices || []);
      setRecentEvents(eventsData.events || []);

      // Determine overall system status
      const hasAlarms = eventsData.events?.some((event: AlarmEvent) =>
        event.severity === 'critical' && !event.resolved
      );
      const hasWarnings = eventsData.events?.some((event: AlarmEvent) =>
        event.severity === 'high' && !event.resolved
      );

      if (hasAlarms) {
        setSystemStatus('alarm');
      } else if (hasWarnings) {
        setSystemStatus('warning');
      } else {
        setSystemStatus('all_clear');
      }

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error occurred');
    } finally {
      setLoading(false);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'online':
      case 'closed':
      case 'armed':
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case 'warning':
      case 'open':
        return <AlertTriangle className="h-5 w-5 text-yellow-500" />;
      case 'offline':
      case 'alarm':
      case 'motion':
        return <XCircle className="h-5 w-5 text-red-500" />;
      default:
        return <Clock className="h-5 w-5 text-gray-500" />;
    }
  };

  const getStatusBadge = (status: string) => {
    const variants = {
      online: 'default',
      offline: 'destructive',
      warning: 'secondary',
      armed: 'default',
      disarmed: 'outline',
      open: 'destructive',
      closed: 'default',
      motion: 'destructive'
    } as const;

    return (
      <Badge variant={variants[status as keyof typeof variants] || 'outline'}>
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </Badge>
    );
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'text-red-600 bg-red-50 border-red-200';
      case 'high': return 'text-orange-600 bg-orange-50 border-orange-200';
      case 'medium': return 'text-yellow-600 bg-yellow-50 border-yellow-200';
      case 'low': return 'text-blue-600 bg-blue-50 border-blue-200';
      default: return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  if (loading) {
    return (
      <div className={`flex items-center justify-center h-64 ${className}`}>
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <Alert className={`${className}`}>
        <AlertTriangle className="h-4 w-4" />
        <AlertDescription>
          Error loading alarm data: {error}
          <Button
            variant="outline"
            size="sm"
            onClick={fetchAlarmData}
            className="ml-2"
          >
            Retry
          </Button>
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <div className={`space-y-6 ${className}`}>
      {/* System Status Overview */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-6 w-6" />
            Alarm System Overview
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-600">{nestDevices.length}</div>
              <div className="text-sm text-gray-600">Nest Protect Devices</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">{ringDevices.length}</div>
              <div className="text-sm text-gray-600">Ring Devices</div>
            </div>
            <div className="text-center">
              <div className={`text-2xl font-bold ${
                systemStatus === 'alarm' ? 'text-red-600' :
                systemStatus === 'warning' ? 'text-yellow-600' :
                'text-green-600'
              }`}>
                {systemStatus === 'alarm' ? 'ALARM' :
                 systemStatus === 'warning' ? 'WARNING' : 'ALL CLEAR'}
              </div>
              <div className="text-sm text-gray-600">System Status</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Nest Protect Devices */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Smoke className="h-5 w-5" />
            Nest Protect Devices
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {nestDevices.map((device) => (
              <Card key={device.id} className="p-4">
                <div className="flex items-center justify-between mb-2">
                  <h4 className="font-semibold">{device.name}</h4>
                  {getStatusIcon(device.status)}
                </div>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span>Location:</span>
                    <span>{device.location}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Battery:</span>
                    <div className="flex items-center gap-1">
                      <Battery className="h-4 w-4" />
                      <span>{device.batteryLevel}%</span>
                    </div>
                  </div>
                  <div className="flex justify-between">
                    <span>Smoke:</span>
                    {getStatusBadge(device.smokeStatus)}
                  </div>
                  <div className="flex justify-between">
                    <span>CO:</span>
                    {getStatusBadge(device.coStatus)}
                  </div>
                  <div className="flex justify-between">
                    <span>Last Seen:</span>
                    <span className="text-xs">{new Date(device.lastSeen).toLocaleTimeString()}</span>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Ring Alarm Devices */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bell className="h-5 w-5" />
            Ring Alarm System
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {ringDevices.map((device) => (
              <Card key={device.id} className="p-4">
                <div className="flex items-center justify-between mb-2">
                  <h4 className="font-semibold">{device.name}</h4>
                  {getStatusIcon(device.status)}
                </div>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span>Type:</span>
                    <span className="capitalize">{device.type.replace('_', ' ')}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Location:</span>
                    <span>{device.location}</span>
                  </div>
                  {device.batteryLevel && (
                    <div className="flex justify-between">
                      <span>Battery:</span>
                      <div className="flex items-center gap-1">
                        <Battery className="h-4 w-4" />
                        <span>{device.batteryLevel}%</span>
                      </div>
                    </div>
                  )}
                  <div className="flex justify-between">
                    <span>Status:</span>
                    {getStatusBadge(device.status)}
                  </div>
                  <div className="flex justify-between">
                    <span>Last Event:</span>
                    <span className="text-xs">{new Date(device.lastEvent).toLocaleTimeString()}</span>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Recent Alerts */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5" />
            Recent Alerts (Last 24 Hours)
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {recentEvents.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                <CheckCircle className="h-12 w-12 mx-auto mb-2 text-green-500" />
                <p>No alerts in the last 24 hours</p>
              </div>
            ) : (
              recentEvents.map((event) => (
                <Alert key={event.id} className={getSeverityColor(event.severity)}>
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="font-semibold">{event.description}</div>
                      <div className="text-sm opacity-75">
                        {event.deviceName} • {new Date(event.timestamp).toLocaleString()}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant="outline">{event.severity}</Badge>
                      {event.resolved ? (
                        <CheckCircle className="h-4 w-4 text-green-500" />
                      ) : (
                        <AlertTriangle className="h-4 w-4 text-red-500" />
                      )}
                    </div>
                  </div>
                </Alert>
              ))
            )}
          </div>
        </CardContent>
      </Card>

      {/* Action Buttons */}
      <div className="flex gap-4">
        <Button onClick={fetchAlarmData} variant="outline">
          <Wifi className="h-4 w-4 mr-2" />
          Refresh Status
        </Button>
        <Button variant="outline">
          <Settings className="h-4 w-4 mr-2" />
          Configure Alarms
        </Button>
      </div>
    </div>
  );
};

export default AlarmDashboard;
