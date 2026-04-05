/**
 * Enhanced Dashboard Component
 *
 * Main dashboard with navigation between Cameras, Alarms, and Energy monitoring
 * pages. Provides unified home security and energy management interface.
 */

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Camera,
  Shield,
  Zap,
  BarChart3,
  Settings,
  Home,
  Menu,
  X,
  Bell,
  Activity
} from 'lucide-react';

// Import dashboard components
import CameraDashboard from '../components/cameras/CameraDashboard';
import AlarmDashboard from '../components/alarms/AlarmDashboard';
import EnergyDashboard from '../components/energy/EnergyDashboard';

type DashboardPage = 'cameras' | 'alarms' | 'energy' | 'analytics' | 'settings';

interface DashboardStats {
  cameras: {
    total: number;
    online: number;
    offline: number;
  };
  alarms: {
    total: number;
    active: number;
    warnings: number;
  };
  energy: {
    total_devices: number;
    active_devices: number;
    daily_cost: number;
    current_power: number;
  };
}

interface DashboardProps {
  className?: string;
}

export const Dashboard: React.FC<DashboardProps> = ({ className }) => {
  const [currentPage, setCurrentPage] = useState<DashboardPage>('cameras');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboardStats();
    const interval = setInterval(fetchDashboardStats, 60000); // Update every minute
    return () => clearInterval(interval);
  }, []);

  const fetchDashboardStats = async () => {
    try {
      // Fetch stats from all systems
      const [camerasResponse, alarmsResponse, energyResponse] = await Promise.all([
        fetch('/api/cameras/stats'),
        fetch('/api/alarms/stats'),
        fetch('/api/energy/stats')
      ]);

      const camerasStats = camerasResponse.ok ? await camerasResponse.json() : { total: 0, online: 0, offline: 0 };
      const alarmsStats = alarmsResponse.ok ? await alarmsResponse.json() : { total: 0, active: 0, warnings: 0 };
      const energyStats = energyResponse.ok ? await energyResponse.json() : {
        total_devices: 0,
        active_devices: 0,
        daily_cost: 0,
        current_power: 0
      };

      setStats({
        cameras: camerasStats,
        alarms: alarmsStats,
        energy: energyStats
      });
    } catch (error) {
      console.error('Failed to fetch dashboard stats:', error);
    } finally {
      setLoading(false);
    }
  };

  const navigationItems = [
    {
      id: 'cameras' as DashboardPage,
      label: 'Cameras',
      icon: Camera,
      color: 'text-blue-600',
      bgColor: 'bg-blue-50',
      borderColor: 'border-blue-200'
    },
    {
      id: 'alarms' as DashboardPage,
      label: 'Alarms',
      icon: Shield,
      color: 'text-red-600',
      bgColor: 'bg-red-50',
      borderColor: 'border-red-200'
    },
    {
      id: 'energy' as DashboardPage,
      label: 'Energy',
      icon: Zap,
      color: 'text-green-600',
      bgColor: 'bg-green-50',
      borderColor: 'border-green-200'
    },
    {
      id: 'analytics' as DashboardPage,
      label: 'Analytics',
      icon: BarChart3,
      color: 'text-purple-600',
      bgColor: 'bg-purple-50',
      borderColor: 'border-purple-200'
    },
    {
      id: 'settings' as DashboardPage,
      label: 'Settings',
      icon: Settings,
      color: 'text-gray-600',
      bgColor: 'bg-gray-50',
      borderColor: 'border-gray-200'
    }
  ];

  const getPageStats = (page: DashboardPage) => {
    if (!stats) return null;

    switch (page) {
      case 'cameras':
        return {
          total: stats.cameras.total,
          active: stats.cameras.online,
          status: stats.cameras.offline > 0 ? 'warning' : 'good'
        };
      case 'alarms':
        return {
          total: stats.alarms.total,
          active: stats.alarms.active,
          status: stats.alarms.warnings > 0 ? 'warning' : 'good'
        };
      case 'energy':
        return {
          total: stats.energy.total_devices,
          active: stats.energy.active_devices,
          status: 'good'
        };
      default:
        return null;
    }
  };

  const renderCurrentPage = () => {
    switch (currentPage) {
      case 'cameras':
        return <CameraDashboard />;
      case 'alarms':
        return <AlarmDashboard />;
      case 'energy':
        return <EnergyDashboard />;
      case 'analytics':
        return (
          <div className="text-center py-16">
            <BarChart3 className="h-16 w-16 mx-auto mb-4 text-purple-500" />
            <h2 className="text-2xl font-bold mb-2">Analytics Dashboard</h2>
            <p className="text-gray-600">Advanced analytics and reporting features coming soon!</p>
          </div>
        );
      case 'settings':
        return (
          <div className="text-center py-16">
            <Settings className="h-16 w-16 mx-auto mb-4 text-gray-500" />
            <h2 className="text-2xl font-bold mb-2">Settings</h2>
            <p className="text-gray-600">System configuration and preferences coming soon!</p>
          </div>
        );
      default:
        return <CameraDashboard />;
    }
  };

  return (
    <div className={`min-h-screen bg-gray-50 ${className}`}>
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center gap-4">
              <Button
                variant="ghost"
                size="sm"
                className="md:hidden"
                onClick={() => setSidebarOpen(!sidebarOpen)}
              >
                {sidebarOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
              </Button>

              <div className="flex items-center gap-2">
                <Home className="h-6 w-6 text-blue-600" />
                <h1 className="text-xl font-bold text-gray-900">
                  Home Security & Energy Monitoring
                </h1>
              </div>
            </div>

            {/* Quick Stats */}
            {stats && (
              <div className="hidden md:flex items-center gap-4">
                <div className="flex items-center gap-2">
                  <Camera className="h-4 w-4 text-blue-600" />
                  <span className="text-sm">
                    {stats.cameras.online}/{stats.cameras.total} Cameras
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <Shield className="h-4 w-4 text-red-600" />
                  <span className="text-sm">
                    {stats.alarms.total} Alarms
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <Zap className="h-4 w-4 text-green-600" />
                  <span className="text-sm">
                    {stats.energy.active_devices}/{stats.energy.total_devices} Devices
                  </span>
                </div>
              </div>
            )}
          </div>
        </div>
      </header>

      <div className="flex">
        {/* Sidebar */}
        <aside className={`
          fixed inset-y-0 left-0 z-50 w-64 bg-white shadow-lg transform transition-transform duration-300 ease-in-out
          md:relative md:translate-x-0 md:shadow-none
          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
        `}>
          <div className="flex flex-col h-full">
            <div className="p-4 border-b">
              <h2 className="text-lg font-semibold text-gray-800">Navigation</h2>
            </div>

            <nav className="flex-1 p-4 space-y-2">
              {navigationItems.map((item) => {
                const Icon = item.icon;
                const pageStats = getPageStats(item.id);
                const isActive = currentPage === item.id;

                return (
                  <Button
                    key={item.id}
                    variant={isActive ? "default" : "ghost"}
                    className={`w-full justify-start h-12 ${isActive ? '' : 'hover:bg-gray-100'}`}
                    onClick={() => {
                      setCurrentPage(item.id);
                      setSidebarOpen(false);
                    }}
                  >
                    <div className="flex items-center gap-3 w-full">
                      <div className={`
                        p-2 rounded-lg
                        ${isActive ? 'bg-white text-blue-600' : `${item.bgColor} ${item.color}`}
                      `}>
                        <Icon className="h-5 w-5" />
                      </div>

                      <div className="flex-1 text-left">
                        <div className="font-medium">{item.label}</div>
                        {pageStats && (
                          <div className="text-xs text-gray-500">
                            {pageStats.active}/{pageStats.total} active
                          </div>
                        )}
                      </div>

                      {pageStats && pageStats.status === 'warning' && (
                        <Badge variant="destructive" className="text-xs">
                          !
                        </Badge>
                      )}
                    </div>
                  </Button>
                );
              })}
            </nav>

            {/* Footer */}
            <div className="p-4 border-t">
              <div className="text-xs text-gray-500 text-center">
                Home Security & Energy Dashboard v2.0
              </div>
            </div>
          </div>
        </aside>

        {/* Main Content */}
        <main className="flex-1 md:ml-0">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
            {/* Page Header */}
            <div className="mb-6">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-2xl font-bold text-gray-900 capitalize">
                    {currentPage} Dashboard
                  </h2>
                  <p className="text-gray-600 mt-1">
                    {currentPage === 'cameras' && 'Monitor and control your security cameras'}
                    {currentPage === 'alarms' && 'Manage Nest Protect and Ring alarm systems'}
                    {currentPage === 'energy' && 'Track energy usage and control smart devices'}
                    {currentPage === 'analytics' && 'View detailed analytics and reports'}
                    {currentPage === 'settings' && 'Configure system settings and preferences'}
                  </p>
                </div>

                {/* Page-specific actions */}
                <div className="flex gap-2">
                  {currentPage === 'cameras' && (
                    <Button variant="outline">
                      <Camera className="h-4 w-4 mr-2" />
                      Add Camera
                    </Button>
                  )}
                  {currentPage === 'alarms' && (
                    <Button variant="outline">
                      <Bell className="h-4 w-4 mr-2" />
                      Test Alarms
                    </Button>
                  )}
                  {currentPage === 'energy' && (
                    <Button variant="outline">
                      <Activity className="h-4 w-4 mr-2" />
                      View Analytics
                    </Button>
                  )}
                </div>
              </div>
            </div>

            {/* Page Content */}
            <div className="space-y-6">
              {loading ? (
                <div className="flex items-center justify-center h-64">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                </div>
              ) : (
                renderCurrentPage()
              )}
            </div>
          </div>
        </main>
      </div>

      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black bg-opacity-50 md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}
    </div>
  );
};

export default Dashboard;
