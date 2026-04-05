/**
 * Onboarding Dashboard Component
 *
 * Progressive device onboarding interface for discovering and configuring
 * various device types including Tapo P115 smart plugs, Nest Protect,
 * Ring devices, and USB webcams.
 */

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Search,
  CheckCircle,
  AlertCircle,
  Clock,
  Zap,
  Shield,
  Camera,
  Wifi,
  Settings,
  ArrowRight,
  ArrowLeft,
  Home,
  Smartphone,
  Monitor
} from 'lucide-react';

interface DiscoveredDevice {
  device_id: string;
  device_type: 'tapo_p115' | 'nest_protect' | 'ring' | 'webcam';
  display_name: string;
  ip_address?: string;
  mac_address?: string;
  model: string;
  location?: string;
  capabilities: string[];
  requires_auth: boolean;
  status: 'discovered' | 'configured' | 'error';
}

interface OnboardingStep {
  id: string;
  title: string;
  description: string;
  icon: React.ReactNode;
  status: 'pending' | 'in_progress' | 'completed' | 'skipped';
}

interface OnboardingProgress {
  current_step: number;
  total_devices_discovered: number;
  devices_configured: number;
  completed_steps: string[];
  onboarding_complete: boolean;
  last_updated: string;
}

export const OnboardingDashboard: React.FC = () => {
  const [currentStep, setCurrentStep] = useState(0);
  const [discoveredDevices, setDiscoveredDevices] = useState<DiscoveredDevice[]>([]);
  const [onboardingProgress, setOnboardingProgress] = useState<OnboardingProgress | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onboardingSteps: OnboardingStep[] = [
    {
      id: 'discovery',
      title: 'Device Discovery',
      description: 'Scanning for available devices on your network',
      icon: <Search className="h-5 w-5" />,
      status: 'in_progress'
    },
    {
      id: 'configuration',
      title: 'Device Configuration',
      description: 'Configure device names, locations, and settings',
      icon: <Settings className="h-5 w-5" />,
      status: 'pending'
    },
    {
      id: 'authentication',
      title: 'Authentication Setup',
      description: 'Set up authentication for protected devices',
      icon: <Shield className="h-5 w-5" />,
      status: 'pending'
    },
    {
      id: 'integration',
      title: 'Integration Setup',
      description: 'Configure device integrations and automation',
      icon: <Wifi className="h-5 w-5" />,
      status: 'pending'
    },
    {
      id: 'completion',
      title: 'Onboarding Complete',
      description: 'Review and finalize your device setup',
      icon: <CheckCircle className="h-5 w-5" />,
      status: 'pending'
    }
  ];

  useEffect(() => {
    // Initialize onboarding
    startDeviceDiscovery();
  }, []);

  const startDeviceDiscovery = async () => {
    setLoading(true);
    setError(null);

    try {
      // Simulate device discovery API call
      await new Promise(resolve => setTimeout(resolve, 2000));

      // Mock discovered devices
      const mockDevices: DiscoveredDevice[] = [
        {
          device_id: 'tapo_p115_001',
          device_type: 'tapo_p115',
          display_name: 'Smart Plug 101',
          ip_address: '192.168.1.101',
          mac_address: '00:11:22:33:44:55',
          model: 'Tapo P115',
          location: 'Living Room',
          capabilities: ['energy_monitoring', 'power_control', 'scheduling'],
          requires_auth: true,
          status: 'discovered'
        },
        {
          device_id: 'tapo_p115_002',
          device_type: 'tapo_p115',
          display_name: 'Smart Plug 102',
          ip_address: '192.168.1.102',
          mac_address: '00:11:22:33:44:56',
          model: 'Tapo P115',
          location: 'Kitchen',
          capabilities: ['energy_monitoring', 'power_control', 'scheduling'],
          requires_auth: true,
          status: 'discovered'
        },
        {
          device_id: 'usb_webcam_0',
          device_type: 'webcam',
          display_name: 'USB Webcam',
          model: 'USB Webcam',
          location: 'Office',
          capabilities: ['video_streaming', 'snapshot_capture'],
          requires_auth: false,
          status: 'discovered'
        },
        {
          device_id: 'nest_protect_001',
          device_type: 'nest_protect',
          display_name: 'Nest Protect - Kitchen',
          model: 'Nest Protect 2nd Gen',
          location: 'Kitchen',
          capabilities: ['smoke_detection', 'co_detection', 'battery_monitoring'],
          requires_auth: true,
          status: 'discovered'
        }
      ];

      setDiscoveredDevices(mockDevices);
      setCurrentStep(1); // Move to configuration step

      // Update progress
      setOnboardingProgress({
        current_step: 1,
        total_devices_discovered: mockDevices.length,
        devices_configured: 0,
        completed_steps: ['discovery'],
        onboarding_complete: false,
        last_updated: new Date().toISOString()
      });

    } catch (err) {
      setError('Failed to discover devices. Please check your network connection.');
    } finally {
      setLoading(false);
    }
  };

  const updateDeviceConfiguration = (deviceId: string, updates: Partial<DiscoveredDevice>) => {
    setDiscoveredDevices(prev =>
      prev.map(device =>
        device.device_id === deviceId
          ? { ...device, ...updates, status: 'configured' as const }
          : device
      )
    );
  };

  const getDeviceIcon = (deviceType: string) => {
    switch (deviceType) {
      case 'tapo_p115':
        return <Zap className="h-5 w-5 text-blue-500" />;
      case 'nest_protect':
        return <Shield className="h-5 w-5 text-red-500" />;
      case 'ring':
        return <Smartphone className="h-5 w-5 text-yellow-500" />;
      case 'webcam':
        return <Camera className="h-5 w-5 text-green-500" />;
      default:
        return <Monitor className="h-5 w-5 text-gray-500" />;
    }
  };

  const getDeviceTypeLabel = (deviceType: string) => {
    switch (deviceType) {
      case 'tapo_p115':
        return 'Tapo P115 Smart Plug';
      case 'nest_protect':
        return 'Nest Protect';
      case 'ring':
        return 'Ring Device';
      case 'webcam':
        return 'USB Webcam';
      default:
        return 'Unknown Device';
    }
  };

  const renderDiscoveryStep = () => (
    <div className="space-y-6">
      <div className="text-center">
        <Search className="h-16 w-16 mx-auto mb-4 text-blue-500" />
        <h2 className="text-2xl font-bold mb-2">Discovering Your Devices</h2>
        <p className="text-gray-600">
          Scanning your network for Tapo P115 smart plugs, Nest Protect devices, Ring alarms, and USB webcams...
        </p>
      </div>

      {loading && (
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-center gap-2">
            <AlertCircle className="h-5 w-5 text-red-600" />
            <span className="text-red-800">{error}</span>
          </div>
        </div>
      )}
    </div>
  );

  const renderConfigurationStep = () => (
    <div className="space-y-6">
      <div className="text-center">
        <Settings className="h-16 w-16 mx-auto mb-4 text-green-500" />
        <h2 className="text-2xl font-bold mb-2">Configure Your Devices</h2>
        <p className="text-gray-600">
          Give your devices friendly names and assign them to locations for easy management.
        </p>
      </div>

      <div className="grid gap-4">
        {discoveredDevices.map((device) => (
          <DeviceConfigCard
            key={device.device_id}
            device={device}
            onUpdate={(updates) => updateDeviceConfiguration(device.device_id, updates)}
          />
        ))}
      </div>

      <div className="flex justify-between">
        <Button variant="outline" onClick={() => setCurrentStep(0)}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Discovery
        </Button>
        <Button onClick={() => setCurrentStep(2)}>
          Continue to Authentication
          <ArrowRight className="h-4 w-4 ml-2" />
        </Button>
      </div>
    </div>
  );

  const renderAuthenticationStep = () => (
    <div className="space-y-6">
      <div className="text-center">
        <Shield className="h-16 w-16 mx-auto mb-4 text-purple-500" />
        <h2 className="text-2xl font-bold mb-2">Authentication Setup</h2>
        <p className="text-gray-600">
          Set up authentication for devices that require it to enable full functionality.
        </p>
      </div>

      <div className="space-y-4">
        {discoveredDevices.filter(device => device.requires_auth).map((device) => (
          <Card key={device.device_id}>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                {getDeviceIcon(device.device_type)}
                {device.display_name}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div>
                  <Label>Device Type</Label>
                  <p className="text-sm text-gray-600">{getDeviceTypeLabel(device.device_type)}</p>
                </div>
                <div>
                  <Label>Location</Label>
                  <p className="text-sm text-gray-600">{device.location}</p>
                </div>
                <Button variant="outline" className="w-full">
                  Set Up Authentication
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="flex justify-between">
        <Button variant="outline" onClick={() => setCurrentStep(1)}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Configuration
        </Button>
        <Button onClick={() => setCurrentStep(3)}>
          Continue to Integration
          <ArrowRight className="h-4 w-4 ml-2" />
        </Button>
      </div>
    </div>
  );

  const renderIntegrationStep = () => (
    <div className="space-y-6">
      <div className="text-center">
        <Wifi className="h-16 w-16 mx-auto mb-4 text-orange-500" />
        <h2 className="text-2xl font-bold mb-2">Integration Setup</h2>
        <p className="text-gray-600">
          Configure how your devices work together and set up automation rules.
        </p>
      </div>

      <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
        <h3 className="text-lg font-semibold mb-4">Smart Integration Recommendations</h3>
        <div className="space-y-3">
          <div className="flex items-center gap-3">
            <CheckCircle className="h-5 w-5 text-green-600" />
            <span>Link Nest Protect smoke alerts with smart plug shutdown</span>
          </div>
          <div className="flex items-center gap-3">
            <CheckCircle className="h-5 w-5 text-green-600" />
            <span>Set up whole-house energy management schedule</span>
          </div>
          <div className="flex items-center gap-3">
            <CheckCircle className="h-5 w-5 text-green-600" />
            <span>Configure camera motion alerts with Ring doorbell</span>
          </div>
        </div>
      </div>

      <div className="flex justify-between">
        <Button variant="outline" onClick={() => setCurrentStep(2)}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Authentication
        </Button>
        <Button onClick={() => setCurrentStep(4)}>
          Complete Setup
          <ArrowRight className="h-4 w-4 ml-2" />
        </Button>
      </div>
    </div>
  );

  const renderCompletionStep = () => (
    <div className="space-y-6">
      <div className="text-center">
        <CheckCircle className="h-16 w-16 mx-auto mb-4 text-green-500" />
        <h2 className="text-2xl font-bold mb-2">Onboarding Complete!</h2>
        <p className="text-gray-600">
          Your devices have been successfully configured and are ready to use.
        </p>
      </div>

      <div className="bg-green-50 border border-green-200 rounded-lg p-6">
        <h3 className="text-lg font-semibold mb-4">Setup Summary</h3>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-sm text-gray-600">Total Devices</p>
            <p className="text-2xl font-bold text-green-600">{discoveredDevices.length}</p>
          </div>
          <div>
            <p className="text-sm text-gray-600">Configured</p>
            <p className="text-2xl font-bold text-green-600">
              {discoveredDevices.filter(d => d.status === 'configured').length}
            </p>
          </div>
        </div>
      </div>

      <div className="space-y-4">
        <h3 className="text-lg font-semibold">Your Devices</h3>
        {discoveredDevices.map((device) => (
          <div key={device.device_id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
            <div className="flex items-center gap-3">
              {getDeviceIcon(device.device_type)}
              <div>
                <p className="font-medium">{device.display_name}</p>
                <p className="text-sm text-gray-600">{device.location}</p>
              </div>
            </div>
            <Badge variant={device.status === 'configured' ? 'default' : 'outline'}>
              {device.status === 'configured' ? 'Configured' : 'Pending'}
            </Badge>
          </div>
        ))}
      </div>

      <div className="flex justify-center">
        <Button size="lg" onClick={() => window.location.href = '/dashboard'}>
          <Home className="h-5 w-5 mr-2" />
          Go to Dashboard
        </Button>
      </div>
    </div>
  );

  const renderCurrentStep = () => {
    switch (currentStep) {
      case 0:
        return renderDiscoveryStep();
      case 1:
        return renderConfigurationStep();
      case 2:
        return renderAuthenticationStep();
      case 3:
        return renderIntegrationStep();
      case 4:
        return renderCompletionStep();
      default:
        return renderDiscoveryStep();
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-4xl mx-auto px-4">
        {/* Progress Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-4">
            <h1 className="text-3xl font-bold">Device Onboarding</h1>
            {onboardingProgress && (
              <Badge variant="outline">
                {onboardingProgress.devices_configured} / {onboardingProgress.total_devices_discovered} configured
              </Badge>
            )}
          </div>

          <div className="space-y-2">
            <Progress value={(currentStep / (onboardingSteps.length - 1)) * 100} className="h-2" />
            <div className="flex justify-between text-sm text-gray-600">
              {onboardingSteps.map((step, index) => (
                <div key={step.id} className="flex items-center gap-2">
                  {step.status === 'completed' ? (
                    <CheckCircle className="h-4 w-4 text-green-600" />
                  ) : step.status === 'in_progress' ? (
                    <Clock className="h-4 w-4 text-blue-600" />
                  ) : (
                    <div className="h-4 w-4 rounded-full border-2 border-gray-300" />
                  )}
                  <span className={currentStep >= index ? 'text-gray-900' : 'text-gray-400'}>
                    {step.title}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Current Step Content */}
        <Card>
          <CardContent className="p-8">
            {renderCurrentStep()}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

interface DeviceConfigCardProps {
  device: DiscoveredDevice;
  onUpdate: (updates: Partial<DiscoveredDevice>) => void;
}

const DeviceConfigCard: React.FC<DeviceConfigCardProps> = ({ device, onUpdate }) => {
  const [displayName, setDisplayName] = useState(device.display_name);
  const [location, setLocation] = useState(device.location || '');

  const handleSave = () => {
    onUpdate({
      display_name: displayName,
      location: location
    });
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          {device.device_type === 'tapo_p115' && <Zap className="h-5 w-5 text-blue-500" />}
          {device.device_type === 'nest_protect' && <Shield className="h-5 w-5 text-red-500" />}
          {device.device_type === 'ring' && <Smartphone className="h-5 w-5 text-yellow-500" />}
          {device.device_type === 'webcam' && <Camera className="h-5 w-5 text-green-500" />}
          {device.model}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
          <Label htmlFor={`name-${device.device_id}`}>Device Name</Label>
          <Input
            id={`name-${device.device_id}`}
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            placeholder="Enter a friendly name"
          />
        </div>

        <div>
          <Label htmlFor={`location-${device.device_id}`}>Location</Label>
          <Input
            id={`location-${device.device_id}`}
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            placeholder="Enter device location"
          />
        </div>

        {device.ip_address && (
          <div>
            <Label>IP Address</Label>
            <p className="text-sm text-gray-600">{device.ip_address}</p>
          </div>
        )}

        <div>
          <Label>Capabilities</Label>
          <div className="flex flex-wrap gap-2 mt-1">
            {device.capabilities.map((capability) => (
              <Badge key={capability} variant="outline" className="text-xs">
                {capability.replace('_', ' ')}
              </Badge>
            ))}
          </div>
        </div>

        <Button onClick={handleSave} className="w-full">
          Save Configuration
        </Button>
      </CardContent>
    </Card>
  );
};

export default OnboardingDashboard;
