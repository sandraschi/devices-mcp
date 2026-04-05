/**
 * Lightweight Energy Chart Component
 *
 * Uses Chart.js for lightweight, responsive energy consumption visualization
 * Optimized for P115 data patterns and real-time updates.
 */

import React, { useEffect, useRef, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  BarChart3,
  TrendingUp,
  TrendingDown,
  RefreshCw,
  Download,
  Maximize2,
  Calendar,
  Zap
} from 'lucide-react';

interface EnergyDataPoint {
  timestamp: string;
  power: number;
  cost: number;
  device_id?: string;
}

interface EnergyChartProps {
  deviceId?: string;
  timeRange: 'hour' | 'day' | 'week';
  data: EnergyDataPoint[];
  loading?: boolean;
  className?: string;
}

export const EnergyChart: React.FC<EnergyChartProps> = ({
  deviceId,
  timeRange,
  data,
  loading = false,
  className
}) => {
  const chartRef = useRef<HTMLCanvasElement>(null);
  const chartInstanceRef = useRef<any>(null);
  const [chartType, setChartType] = useState<'line' | 'bar'>('line');
  const [showCost, setShowCost] = useState(false);

  // Initialize Chart.js dynamically (lightweight)
  useEffect(() => {
    const initChart = async () => {
      const { Chart, registerables } = await import('chart.js/auto');
      Chart.register(...registerables);

      if (chartRef.current && data.length > 0) {
        createChart(Chart);
      }
    };

    initChart();
  }, [data, chartType, showCost]);

  const createChart = (Chart: any) => {
    if (chartInstanceRef.current) {
      chartInstanceRef.current.destroy();
    }

    const ctx = chartRef.current?.getContext('2d');
    if (!ctx || !data.length) return;

    // Prepare data based on time range
    const { labels, powerData, costData } = prepareChartData();

    chartInstanceRef.current = new Chart(ctx, {
      type: chartType,
      data: {
        labels,
        datasets: [
          {
            label: 'Power Consumption (W)',
            data: powerData,
            borderColor: '#3b82f6',
            backgroundColor: chartType === 'bar' ? 'rgba(59, 130, 246, 0.1)' : 'rgba(59, 130, 246, 0.05)',
            borderWidth: 2,
            fill: chartType === 'line',
            tension: 0.4,
            yAxisID: 'y'
          },
          ...(showCost ? [{
            label: 'Cost (USD)',
            data: costData,
            borderColor: '#10b981',
            backgroundColor: chartType === 'bar' ? 'rgba(16, 185, 129, 0.1)' : 'rgba(16, 185, 129, 0.05)',
            borderWidth: 2,
            fill: chartType === 'line',
            tension: 0.4,
            yAxisID: 'y1'
          }] : [])
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: 'index',
          intersect: false,
        },
        plugins: {
          legend: {
            position: 'top',
            labels: {
              usePointStyle: true,
              padding: 20
            }
          },
          tooltip: {
            backgroundColor: 'rgba(0, 0, 0, 0.8)',
            titleColor: 'white',
            bodyColor: 'white',
            borderColor: '#374151',
            borderWidth: 1,
            callbacks: {
              title: (context) => {
                const dataIndex = context[0].dataIndex;
                return labels[dataIndex];
              },
              label: (context) => {
                const value = context.parsed.y;
                const label = context.dataset.label;

                if (label?.includes('Power')) {
                  return `${label}: ${value.toFixed(1)}W`;
                } else if (label?.includes('Cost')) {
                  return `${label}: $${value.toFixed(3)}`;
                }
                return `${label}: ${value}`;
              }
            }
          }
        },
        scales: {
          x: {
            display: true,
            title: {
              display: true,
              text: getXAxisLabel(),
              color: '#6b7280'
            },
            grid: {
              color: 'rgba(107, 114, 128, 0.1)'
            },
            ticks: {
              color: '#6b7280',
              maxTicksLimit: 8
            }
          },
          y: {
            type: 'linear',
            display: true,
            position: 'left',
            title: {
              display: true,
              text: 'Power (W)',
              color: '#3b82f6'
            },
            grid: {
              color: 'rgba(59, 130, 246, 0.1)'
            },
            ticks: {
              color: '#3b82f6',
              callback: (value) => `${value}W`
            }
          },
          ...(showCost ? {
            y1: {
              type: 'linear',
              display: true,
              position: 'right',
              title: {
                display: true,
                text: 'Cost (USD)',
                color: '#10b981'
              },
              grid: {
                drawOnChartArea: false,
              },
              ticks: {
                color: '#10b981',
                callback: (value) => `$${value.toFixed(3)}`
              }
            }
          } : {})
        },
        animation: {
          duration: 750,
          easing: 'easeInOutQuart'
        }
      }
    });
  };

  const prepareChartData = () => {
    const now = new Date();
    let labels: string[] = [];
    let powerData: number[] = [];
    let costData: number[] = [];

    switch (timeRange) {
      case 'hour':
        // Last 12 hours, 1-hour intervals
        for (let i = 11; i >= 0; i--) {
          const hour = new Date(now.getTime() - i * 60 * 60 * 1000);
          labels.push(hour.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }));

          const hourData = data.filter(d => {
            const dTime = new Date(d.timestamp);
            return dTime.getHours() === hour.getHours() &&
                   dTime.getDate() === hour.getDate();
          });

          const avgPower = hourData.length > 0
            ? hourData.reduce((sum, d) => sum + d.power, 0) / hourData.length
            : 0;
          const totalCost = hourData.reduce((sum, d) => sum + d.cost, 0);

          powerData.push(avgPower);
          costData.push(totalCost);
        }
        break;

      case 'day':
        // Last 24 hours, 1-hour intervals
        for (let i = 23; i >= 0; i--) {
          const hour = new Date(now.getTime() - i * 60 * 60 * 1000);
          labels.push(hour.toLocaleTimeString([], { hour: '2-digit' }));

          const hourData = data.filter(d => {
            const dTime = new Date(d.timestamp);
            return dTime.getHours() === hour.getHours() &&
                   dTime.getDate() === hour.getDate();
          });

          const avgPower = hourData.length > 0
            ? hourData.reduce((sum, d) => sum + d.power, 0) / hourData.length
            : 0;
          const totalCost = hourData.reduce((sum, d) => sum + d.cost, 0);

          powerData.push(avgPower);
          costData.push(totalCost);
        }
        break;

      case 'week':
        // Last 7 days, 1-day intervals
        for (let i = 6; i >= 0; i--) {
          const day = new Date(now.getTime() - i * 24 * 60 * 60 * 1000);
          labels.push(day.toLocaleDateString([], { weekday: 'short', month: 'short', day: 'numeric' }));

          const dayData = data.filter(d => {
            const dTime = new Date(d.timestamp);
            return dTime.getDate() === day.getDate() &&
                   dTime.getMonth() === day.getMonth();
          });

          const avgPower = dayData.length > 0
            ? dayData.reduce((sum, d) => sum + d.power, 0) / dayData.length
            : 0;
          const totalCost = dayData.reduce((sum, d) => sum + d.cost, 0);

          powerData.push(avgPower);
          costData.push(totalCost);
        }
        break;
    }

    return { labels, powerData, costData };
  };

  const getXAxisLabel = () => {
    switch (timeRange) {
      case 'hour': return 'Time (Last 12 Hours)';
      case 'day': return 'Time (Last 24 Hours)';
      case 'week': return 'Date (Last 7 Days)';
      default: return 'Time';
    }
  };

  const getChartTitle = () => {
    const deviceText = deviceId ? ` - ${deviceId}` : '';
    switch (timeRange) {
      case 'hour': return `Energy Consumption (Last 12 Hours)${deviceText}`;
      case 'day': return `Energy Consumption (Last 24 Hours)${deviceText}`;
      case 'week': return `Energy Consumption (Last 7 Days)${deviceText}`;
      default: return `Energy Consumption${deviceText}`;
    }
  };

  const exportChart = () => {
    if (chartInstanceRef.current) {
      const link = document.createElement('a');
      link.download = `energy-chart-${timeRange}-${new Date().toISOString().split('T')[0]}.png`;
      link.href = chartInstanceRef.current.toBase64Image();
      link.click();
    }
  };

  const getStats = () => {
    if (!data.length) return { avgPower: 0, totalCost: 0, peakPower: 0, trend: 'neutral' };

    const avgPower = data.reduce((sum, d) => sum + d.power, 0) / data.length;
    const totalCost = data.reduce((sum, d) => sum + d.cost, 0);
    const peakPower = Math.max(...data.map(d => d.power));

    // Calculate trend (simple comparison of first vs last half)
    const midPoint = Math.floor(data.length / 2);
    const firstHalf = data.slice(0, midPoint);
    const secondHalf = data.slice(midPoint);

    const firstHalfAvg = firstHalf.reduce((sum, d) => sum + d.power, 0) / firstHalf.length;
    const secondHalfAvg = secondHalf.reduce((sum, d) => sum + d.power, 0) / secondHalf.length;

    let trend: 'up' | 'down' | 'neutral' = 'neutral';
    if (secondHalfAvg > firstHalfAvg * 1.05) trend = 'up';
    else if (secondHalfAvg < firstHalfAvg * 0.95) trend = 'down';

    return { avgPower, totalCost, peakPower, trend };
  };

  const stats = getStats();

  if (loading) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BarChart3 className="h-5 w-5" />
            Energy Consumption Chart
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <BarChart3 className="h-5 w-5" />
            {getChartTitle()}
          </CardTitle>

          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setChartType(chartType === 'line' ? 'bar' : 'line')}
            >
              {chartType === 'line' ? <BarChart3 className="h-4 w-4" /> : <TrendingUp className="h-4 w-4" />}
            </Button>

            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowCost(!showCost)}
            >
              <Zap className="h-4 w-4" />
              {showCost ? 'Hide Cost' : 'Show Cost'}
            </Button>

            <Button
              variant="outline"
              size="sm"
              onClick={exportChart}
            >
              <Download className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {/* Quick Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
          <div className="text-center">
            <div className="text-lg font-semibold text-blue-600">
              {stats.avgPower.toFixed(1)}W
            </div>
            <div className="text-xs text-gray-600">Average Power</div>
          </div>
          <div className="text-center">
            <div className="text-lg font-semibold text-green-600">
              ${stats.totalCost.toFixed(3)}
            </div>
            <div className="text-xs text-gray-600">Total Cost</div>
          </div>
          <div className="text-center">
            <div className="text-lg font-semibold text-red-600">
              {stats.peakPower.toFixed(1)}W
            </div>
            <div className="text-xs text-gray-600">Peak Power</div>
          </div>
          <div className="text-center">
            <div className="flex items-center justify-center gap-1">
              {stats.trend === 'up' && <TrendingUp className="h-4 w-4 text-green-600" />}
              {stats.trend === 'down' && <TrendingDown className="h-4 w-4 text-red-600" />}
              {stats.trend === 'neutral' && <div className="h-4 w-4 bg-gray-400 rounded-full" />}
              <span className="text-xs text-gray-600 capitalize">{stats.trend}</span>
            </div>
            <div className="text-xs text-gray-600">Trend</div>
          </div>
        </div>
      </CardHeader>

      <CardContent>
        {data.length === 0 ? (
          <div className="text-center py-16 text-gray-500">
            <BarChart3 className="h-12 w-12 mx-auto mb-4 text-gray-400" />
            <p>No energy data available for the selected time range</p>
            <p className="text-sm mt-2">
              P115 devices provide hourly data for the current day only
            </p>
          </div>
        ) : (
          <div className="relative h-80">
            <canvas ref={chartRef} />
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default EnergyChart;
