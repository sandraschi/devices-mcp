/**
 * Energy Dashboard Component
 *
 * Comprehensive energy monitoring interface for Tapo smart plugs with
 * real-time power consumption, cost analysis, and smart automation.
 */

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Zap,
  DollarSign,
  TrendingUp,
  TrendingDown,
  Power,
  Clock,
  Settings,
  BarChart3,
  Lightbulb,
  Coffee,
  Tv,
  Wifi,
  Battery,
  Activity,
  Grid3X3
} from 'lucide-react';
import EnergyChartContainer from './EnergyChartContainer';

interface SmartPlugDevice {
  id: string;
  name: string;
  location: string;
  deviceModel: string;
  powerState: boolean;
  currentPower: number; // watts
  voltage: number; // volts
  current: number; // amps
  dailyEnergy: number; // kWh
  monthlyEnergy: number; // kWh
  dailyCost: number; // USD
  monthlyCost: number; // USD
  lastSeen: string;
  automationEnabled: boolean;
  powerSchedule: string;
  energySavingMode: boolean;
}

interface EnergyUsageData {
  timestamp: string;
  totalPower: number;
  totalCost: number;
  peakPower: number;
  averagePower: number;
}

interface EnergyDashboardProps {
  className?: string;
}

export const EnergyDashboard: React.FC<EnergyDashboardProps> = ({ className }) => {
  const [smartPlugs, setSmartPlugs] = useState<SmartPlugDevice[]>([]);
  const [energyData, setEnergyData] = useState<EnergyUsageData | null>(null);
  const [usageHistory, setUsageHistory] = useState<EnergyUsageData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedPeriod, setSelectedPeriod] = useState<'day' | 'week' | 'month'>('day');

  useEffect(() => {
    fetchEnergyData();
    const interval = setInterval(fetchEnergyData, 30000); // Update every 30 seconds
    return () => clearInterval(interval);
  }, [selectedPeriod]);

  const fetchEnergyData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Fetch data from energy monitoring systems
      const [devicesResponse, usageResponse, historyResponse] = await Promise.all([
        fetch('/api/energy/devices'),
        fetch('/api/energy/current-usage'),
        fetch(`/api/energy/usage-history?period=${selectedPeriod}`)
      ]);

      if (!devicesResponse.ok || !usageResponse.ok || !historyResponse.ok) {
        throw new Error('Failed to fetch energy data');
      }

      const devicesData = await devicesResponse.json();
      const usageData = await usageResponse.json();
      const historyData = await historyResponse.json();

      setSmartPlugs(devicesData.devices || []);
      setEnergyData(usageData);
      setUsageHistory(historyData.history || []);

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error occurred');
    } finally {
      setLoading(false);
    }
  };

  const toggleDevice = async (deviceId: string, currentState: boolean) => {
    try {
      const response = await fetch(`/api/energy/devices/${deviceId}/toggle`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ power_state: !currentState })
      });

      if (response.ok) {
        fetchEnergyData(); // Refresh data
      }
    } catch (err) {
      console.error('Failed to toggle device:', err);
    }
  };

  const getDeviceIcon = (deviceName: string) => {
    const name = deviceName.toLowerCase();
    if (name.includes('tv') || name.includes('television')) return <Tv className="h-5 w-5" />;
    if (name.includes('coffee') || name.includes('maker')) return <Coffee className="h-5 w-5" />;
    if (name.includes('lamp') || name.includes('light')) return <Lightbulb className="h-5 w-5" />;
    return <Power className="h-5 w-5" />;
  };

  const getPowerStatusColor = (power: number) => {
    if (power === 0) return 'text-gray-500';
    if (power < 50) return 'text-green-500';
    if (power < 200) return 'text-yellow-500';
    return 'text-red-500';
  };

  const getCostTrend = () => {
    if (usageHistory.length < 2) return 'neutral';
    const current = usageHistory[usageHistory.length - 1];
    const previous = usageHistory[usageHistory.length - 2];
    return current.totalCost > previous.totalCost ? 'up' : 'down';
  };

  const getTotalDailyCost = () => {
    return smartPlugs.reduce((sum, device) => sum + device.dailyCost, 0);
  };

  const getTotalMonthlyCost = () => {
    return smartPlugs.reduce((sum, device) => sum + device.monthlyCost, 0);
  };

  const getTotalCurrentPower = () => {
    return smartPlugs.reduce((sum, device) => sum + (device.powerState ? device.currentPower : 0), 0);
  };

  const getActiveDevicesCount = () => {
    return smartPlugs.filter(device => device.powerState).length;
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
      <div className={`text-center py-8 ${className}`}>
        <div className="text-red-500 mb-4">Error loading energy data: {error}</div>
        <Button onClick={fetchEnergyData} variant="outline">
          Retry
        </Button>
      </div>
    );
  }

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Energy Overview */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Zap className="h-6 w-6" />
            Energy Overview
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-600">
                {getTotalCurrentPower().toFixed(1)}W
              </div>
              <div className="text-sm text-gray-600">Current Power</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">
                ${getTotalDailyCost().toFixed(2)}
              </div>
              <div className="text-sm text-gray-600">Today's Cost</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-purple-600">
                ${getTotalMonthlyCost().toFixed(2)}
              </div>
              <div className="text-sm text-gray-600">This Month</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-orange-600">
                {getActiveDevicesCount()}/{smartPlugs.length}
              </div>
              <div className="text-sm text-gray-600">Active Devices</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Energy Charts Tabs */}
      <Tabs defaultValue="overview" className="w-full">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="overview" className="flex items-center gap-2">
            <Grid3X3 className="h-4 w-4" />
            Overview
          </TabsTrigger>
          <TabsTrigger value="charts" className="flex items-center gap-2">
            <BarChart3 className="h-4 w-4" />
            Charts
          </TabsTrigger>
          <TabsTrigger value="devices" className="flex items-center gap-2">
            <Power className="h-4 w-4" />
            Devices
          </TabsTrigger>
          <TabsTrigger value="analytics" className="flex items-center gap-2">
            <Activity className="h-4 w-4" />
            Analytics
          </TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-6">
          {/* Overview content - existing Power Usage Chart and Smart Plugs Status */}
          {renderOverviewContent()}
        </TabsContent>

        <TabsContent value="charts" className="space-y-6">
          <EnergyChartContainer />
        </TabsContent>

        <TabsContent value="devices" className="space-y-6">
          {renderDevicesContent()}
        </TabsContent>

        <TabsContent value="analytics" className="space-y-6">
          {renderAnalyticsContent()}
        </TabsContent>
      </Tabs>
    </div>
  );

  function renderOverviewContent() {
    return (
      <>
        {/* Power Usage Chart */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <BarChart3 className="h-5 w-5" />
                Power Usage Trend
              </div>
              <div className="flex gap-2">
                {(['day', 'week', 'month'] as const).map((period) => (
                  <Button
                    key={period}
                    variant={selectedPeriod === period ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => setSelectedPeriod(period)}
                  >
                    {period.charAt(0).toUpperCase() + period.slice(1)}
                  </Button>
                ))}
              </div>
            </CardTitle>
          </CardHeader>
          <CardContent>
            {usageHistory.length > 0 ? (
              <div className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="text-center">
                    <div className="text-lg font-semibold text-blue-600">
                      {energyData?.averagePower.toFixed(1)}W
                    </div>
                    <div className="text-sm text-gray-600">Average Power</div>
                  </div>
                  <div className="text-center">
                    <div className="text-lg font-semibold text-red-600">
                      {energyData?.peakPower.toFixed(1)}W
                    </div>
                    <div className="text-sm text-gray-600">Peak Power</div>
                  </div>
                  <div className="text-center">
                    <div className="text-lg font-semibold text-green-600">
                      ${energyData?.totalCost.toFixed(2)}
                    </div>
                    <div className="text-sm text-gray-600">Total Cost</div>
                  </div>
                </div>
                {/* Simple chart representation */}
                <div className="h-32 bg-gray-50 rounded-lg p-4 flex items-end gap-1">
                  {usageHistory.slice(-24).map((data, index) => (
                    <div
                      key={index}
                      className="bg-blue-500 rounded-t"
                      style={{
                        height: `${(data.totalPower / Math.max(...usageHistory.map(d => d.totalPower))) * 100}%`,
                        width: '4px'
                      }}
                    />
                  ))}
                </div>
              </div>
            ) : (
              <div className="text-center py-8 text-gray-500">
                <BarChart3 className="h-12 w-12 mx-auto mb-2" />
                <p>No usage data available</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Smart Plugs Status */}
        {renderSmartPlugsStatus()}
      </>
    );
  }

  function renderDevicesContent() {
    return renderSmartPlugsStatus();
  }

  function renderAnalyticsContent() {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-5 w-5" />
            Energy Analytics
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-16">
            <Activity className="h-16 w-16 mx-auto mb-4 text-purple-500" />
            <h2 className="text-2xl font-bold mb-2">Advanced Analytics</h2>
            <p className="text-gray-600">Detailed energy analytics and reporting features coming soon!</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  function renderSmartPlugsStatus() {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Power className="h-5 w-5" />
            Smart Plugs Status
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {smartPlugs.map((device) => (
              <Card key={device.id} className="p-4">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    {getDeviceIcon(device.name)}
                    <h4 className="font-semibold">{device.name}</h4>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant={device.powerState ? 'default' : 'outline'}>
                      {device.powerState ? 'On' : 'Off'}
                    </Badge>
                    {device.automationEnabled && (
                      <Badge variant="secondary" className="text-xs">
                        Auto
                      </Badge>
                    )}
                  </div>
                </div>

                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span>Model:</span>
                    <span className="font-medium">{device.deviceModel}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Location:</span>
                    <span>{device.location}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Current Power:</span>
                    <span className={getPowerStatusColor(device.currentPower)}>
                      {device.powerState ? `${device.currentPower}W` : '0W'}
                    </span>
                  </div>
                  {device.powerState && (
                    <>
                      <div className="flex justify-between">
                        <span>Voltage:</span>
                        <span>{device.voltage.toFixed(1)}V</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Current:</span>
                        <span>{device.current.toFixed(2)}A</span>
                      </div>
                    </>
                  )}
                  <div className="flex justify-between">
                    <span>Daily Usage:</span>
                    <span>{device.dailyEnergy.toFixed(2)} kWh</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Daily Cost:</span>
                    <span className="font-semibold">${device.dailyCost.toFixed(2)}</span>
                  </div>
                  {device.powerSchedule && (
                    <div className="flex justify-between">
                      <span>Schedule:</span>
                      <span className="text-xs">{device.powerSchedule}</span>
                    </div>
                  )}
                  <div className="flex justify-between">
                    <span>Last Seen:</span>
                    <span className="text-xs">{new Date(device.lastSeen).toLocaleTimeString()}</span>
                  </div>
                </div>

                <div className="mt-3 pt-3 border-t">
                  <Button
                    variant={device.powerState ? 'destructive' : 'default'}
                    size="sm"
                    onClick={() => toggleDevice(device.id, device.powerState)}
                    className="w-full"
                  >
                    {device.powerState ? 'Turn Off' : 'Turn On'}
                  </Button>
                </div>
              </Card>
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

      {/* Power Usage Chart */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <BarChart3 className="h-5 w-5" />
              Power Usage Trend
            </div>
            <div className="flex gap-2">
              {(['day', 'week', 'month'] as const).map((period) => (
                <Button
                  key={period}
                  variant={selectedPeriod === period ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setSelectedPeriod(period)}
                >
                  {period.charAt(0).toUpperCase() + period.slice(1)}
                </Button>
              ))}
            </div>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {usageHistory.length > 0 ? (
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="text-center">
                  <div className="text-lg font-semibold text-blue-600">
                    {energyData?.averagePower.toFixed(1)}W
                  </div>
                  <div className="text-sm text-gray-600">Average Power</div>
                </div>
                <div className="text-center">
                  <div className="text-lg font-semibold text-red-600">
                    {energyData?.peakPower.toFixed(1)}W
                  </div>
                  <div className="text-sm text-gray-600">Peak Power</div>
                </div>
                <div className="text-center">
                  <div className="text-lg font-semibold text-green-600">
                    ${energyData?.totalCost.toFixed(2)}
                  </div>
                  <div className="text-sm text-gray-600">Total Cost</div>
                </div>
              </div>
              {/* Simple chart representation */}
              <div className="h-32 bg-gray-50 rounded-lg p-4 flex items-end gap-1">
                {usageHistory.slice(-24).map((data, index) => (
                  <div
                    key={index}
                    className="bg-blue-500 rounded-t"
                    style={{
                      height: `${(data.totalPower / Math.max(...usageHistory.map(d => d.totalPower))) * 100}%`,
                      width: '4px'
                    }}
                  />
                ))}
              </div>
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500">
              <BarChart3 className="h-12 w-12 mx-auto mb-2" />
              <p>No usage data available</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Smart Plugs Status */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Power className="h-5 w-5" />
            Smart Plugs Status
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {smartPlugs.map((device) => (
              <Card key={device.id} className="p-4">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    {getDeviceIcon(device.name)}
                    <h4 className="font-semibold">{device.name}</h4>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant={device.powerState ? 'default' : 'outline'}>
                      {device.powerState ? 'On' : 'Off'}
                    </Badge>
                    {device.automationEnabled && (
                      <Badge variant="secondary" className="text-xs">
                        Auto
                      </Badge>
                    )}
                  </div>
                </div>

                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span>Model:</span>
                    <span className="font-medium">{device.deviceModel}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Location:</span>
                    <span>{device.location}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Current Power:</span>
                    <span className={getPowerStatusColor(device.currentPower)}>
                      {device.powerState ? `${device.currentPower}W` : '0W'}
                    </span>
                  </div>
                  {device.powerState && (
                    <>
                      <div className="flex justify-between">
                        <span>Voltage:</span>
                        <span>{device.voltage.toFixed(1)}V</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Current:</span>
                        <span>{device.current.toFixed(2)}A</span>
                      </div>
                    </>
                  )}
                  <div className="flex justify-between">
                    <span>Daily Usage:</span>
                    <span>{device.dailyEnergy.toFixed(2)} kWh</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Daily Cost:</span>
                    <span className="font-semibold">${device.dailyCost.toFixed(2)}</span>
                  </div>
                  {device.powerSchedule && (
                    <div className="flex justify-between">
                      <span>Schedule:</span>
                      <span className="text-xs">{device.powerSchedule}</span>
                    </div>
                  )}
                  <div className="flex justify-between">
                    <span>Last Seen:</span>
                    <span className="text-xs">{new Date(device.lastSeen).toLocaleTimeString()}</span>
                  </div>
                </div>

                <div className="mt-3 pt-3 border-t">
                  <Button
                    variant={device.powerState ? 'destructive' : 'default'}
                    size="sm"
                    onClick={() => toggleDevice(device.id, device.powerState)}
                    className="w-full"
                  >
                    {device.powerState ? 'Turn Off' : 'Turn On'}
                  </Button>
                </div>
              </Card>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Energy Savings Tips */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Lightbulb className="h-5 w-5" />
            Energy Saving Tips
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <h4 className="font-semibold text-green-600">💡 Quick Wins</h4>
              <ul className="text-sm space-y-1 text-gray-600">
                <li>• Turn off devices when not in use</li>
                <li>• Use smart scheduling for high-power devices</li>
                <li>• Enable automation for lights and entertainment</li>
                <li>• Monitor vampire power consumption</li>
              </ul>
            </div>
            <div className="space-y-2">
              <h4 className="font-semibold text-blue-600">DATA This Month's Savings</h4>
              <div className="text-lg font-bold text-green-600">
                ${(getTotalMonthlyCost() * 0.15).toFixed(2)}
              </div>
              <div className="text-sm text-gray-600">
                Potential savings with optimized usage
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Action Buttons */}
      <div className="flex gap-4">
        <Button onClick={fetchEnergyData} variant="outline">
          <Wifi className="h-4 w-4 mr-2" />
          Refresh Status
        </Button>
        <Button variant="outline">
          <Settings className="h-4 w-4 mr-2" />
          Configure Automation
        </Button>
        <Button variant="outline">
          <BarChart3 className="h-4 w-4 mr-2" />
          View Detailed Analytics
        </Button>
      </div>
    </div>
  );
};

export default EnergyDashboard;
