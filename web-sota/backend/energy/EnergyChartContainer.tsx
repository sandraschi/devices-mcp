/**
 * Energy Chart Container Component
 *
 * Lightweight container for energy charts with time range controls
 * and data management for P115 devices.
 */

import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Calendar,
  Clock,
  BarChart3,
  RefreshCw,
  Info
} from 'lucide-react';
import EnergyChart from './EnergyChart';

interface EnergyChartContainerProps {
  deviceId?: string;
  className?: string;
}

type TimeRange = 'hour' | 'day' | 'week';

export const EnergyChartContainer: React.FC<EnergyChartContainerProps> = ({
  deviceId,
  className
}) => {
  const [timeRange, setTimeRange] = useState<TimeRange>('day');
  const [chartData, setChartData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());

  const timeRanges = [
    { key: 'hour' as TimeRange, label: '12 Hours', icon: Clock },
    { key: 'day' as TimeRange, label: '24 Hours', icon: BarChart3 },
    { key: 'week' as TimeRange, label: '7 Days', icon: Calendar }
  ];

  useEffect(() => {
    fetchChartData();
    const interval = setInterval(fetchChartData, 60000); // Update every minute
    return () => clearInterval(interval);
  }, [timeRange, deviceId]);

  const fetchChartData = async () => {
    try {
      setLoading(true);

      // Simulate P115 data fetching
      // In real implementation, this would call the P115 API
      const mockData = generateMockEnergyData(timeRange, deviceId);
      setChartData(mockData);
      setLastUpdated(new Date());

    } catch (error) {
      console.error('Failed to fetch chart data:', error);
    } finally {
      setLoading(false);
    }
  };

  const generateMockEnergyData = (range: TimeRange, device?: string) => {
    const now = new Date();
    const data: any[] = [];

    let dataPoints = 0;
    let intervalMs = 0;

    switch (range) {
      case 'hour':
        dataPoints = 12;
        intervalMs = 60 * 60 * 1000; // 1 hour
        break;
      case 'day':
        dataPoints = 24;
        intervalMs = 60 * 60 * 1000; // 1 hour
        break;
      case 'week':
        dataPoints = 7;
        intervalMs = 24 * 60 * 60 * 1000; // 1 day
        break;
    }

    for (let i = dataPoints - 1; i >= 0; i--) {
      const timestamp = new Date(now.getTime() - i * intervalMs);

      // Generate realistic energy patterns based on device type and time
      let basePower = 0;
      let powerMultiplier = 1;

      if (device) {
        if (device.includes('coffee')) {
          basePower = 850;
          powerMultiplier = (timestamp.getHours() >= 6 && timestamp.getHours() <= 8) ? 1.0 : 0.1;
        } else if (device.includes('charger')) {
          basePower = 1200;
          powerMultiplier = (timestamp.getHours() >= 22 || timestamp.getHours() <= 6) ? 1.0 : 0.1;
        } else if (device.includes('tv')) {
          basePower = 45;
          powerMultiplier = (timestamp.getHours() >= 18 && timestamp.getHours() <= 23) ? 1.0 : 0.3;
        } else if (device.includes('computer')) {
          basePower = 180;
          powerMultiplier = (timestamp.getHours() >= 9 && timestamp.getHours() <= 17) ? 1.0 : 0.1;
        } else {
          basePower = 50;
          powerMultiplier = 0.5;
        }
      } else {
        // Aggregate data for all devices
        basePower = 300;
        powerMultiplier = 0.8 + Math.sin(timestamp.getHours() / 24 * Math.PI * 2) * 0.3;
      }

      const power = basePower * powerMultiplier + (Math.random() - 0.5) * basePower * 0.1;
      const cost = (power / 1000) * 0.12; // $0.12 per kWh

      data.push({
        timestamp: timestamp.toISOString(),
        power: Math.max(0, power),
        cost: cost,
        device_id: device
      });
    }

    return data;
  };

  const getDataInfo = () => {
    switch (timeRange) {
      case 'hour':
        return {
          description: 'Hourly data for the last 12 hours',
          limitation: 'P115 provides real-time data with hourly aggregation',
          dataPoints: chartData.length
        };
      case 'day':
        return {
          description: 'Hourly data for the last 24 hours',
          limitation: 'Daily consumption resets at midnight',
          dataPoints: chartData.length
        };
      case 'week':
        return {
          description: 'Daily aggregated data for the last 7 days',
          limitation: 'Limited by P115 daily reset - simulated data',
          dataPoints: chartData.length
        };
      default:
        return {
          description: 'Energy consumption data',
          limitation: 'Data availability depends on P115 capabilities',
          dataPoints: chartData.length
        };
    }
  };

  const dataInfo = getDataInfo();

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Chart Controls */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h3 className="text-lg font-semibold">Energy Consumption Chart</h3>
          {deviceId && (
            <Badge variant="outline">
              {deviceId}
            </Badge>
          )}
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={fetchChartData}
            disabled={loading}
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Time Range Selector */}
      <div className="flex items-center gap-2">
        <span className="text-sm text-gray-600">Time Range:</span>
        {timeRanges.map((range) => {
          const Icon = range.icon;
          return (
            <Button
              key={range.key}
              variant={timeRange === range.key ? 'default' : 'outline'}
              size="sm"
              onClick={() => setTimeRange(range.key)}
              className="flex items-center gap-2"
            >
              <Icon className="h-4 w-4" />
              {range.label}
            </Button>
          );
        })}
      </div>

      {/* Data Info */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
        <div className="flex items-start gap-2">
          <Info className="h-4 w-4 text-blue-600 mt-0.5" />
          <div className="text-sm">
            <div className="text-blue-800 font-medium">{dataInfo.description}</div>
            <div className="text-blue-600 mt-1">
              {dataInfo.limitation} • {dataInfo.dataPoints} data points
            </div>
            <div className="text-blue-500 text-xs mt-1">
              Last updated: {lastUpdated.toLocaleTimeString()}
            </div>
          </div>
        </div>
      </div>

      {/* Chart */}
      <EnergyChart
        deviceId={deviceId}
        timeRange={timeRange}
        data={chartData}
        loading={loading}
      />

      {/* P115 Data Limitations Note */}
      {timeRange === 'week' && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
          <div className="flex items-start gap-2">
            <Info className="h-4 w-4 text-yellow-600 mt-0.5" />
            <div className="text-sm">
              <div className="text-yellow-800 font-medium">P115 Data Limitation</div>
              <div className="text-yellow-700 mt-1">
                Weekly data is simulated as P115 devices only store current day data.
                For historical analysis, consider integrating with Home Assistant.
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default EnergyChartContainer;
