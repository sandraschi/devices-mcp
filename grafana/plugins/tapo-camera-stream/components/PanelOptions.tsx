import React from 'react';
import { Field, Input, Select, Switch, InlineField, InlineFieldRow, InlineSwitch } from '@grafana/ui';
import { SelectableValue } from '@grafana/data';

export const PanelOptions = ({ options, onOptionsChange }: any) => {
  const streamTypeOptions: Array<SelectableValue<string>> = [
    { value: 'hls', label: 'HLS' },
    { value: 'rtsp', label: 'RTSP' },
    { value: 'rtmp', label: 'RTMP' },
    { value: 'webrtc', label: 'WebRTC' },
    { value: 'mjpeg', label: 'MJPEG' },
  ];

  const qualityOptions: Array<SelectableValue<string>> = [
    { value: 'auto', label: 'Auto' },
    { value: 'high', label: 'High' },
    { value: 'medium', label: 'Medium' },
    { value: 'low', label: 'Low' },
  ];

  return (
    <div className="editor-row">
      <div className="section gf-form-group">
        <h5>Stream Configuration</h5>

        <Field label="Stream URL" description="URL for the camera stream (RTSP, RTMP, HLS, etc.)">
          <Input
            value={options.streamUrl || ''}
            onChange={(e) => onOptionsChange({ ...options, streamUrl: e.currentTarget.value })}
            placeholder="rtsp://camera-address/stream"
            width={60}
          />
        </Field>

        <Field label="Stream Type" description="Type of video stream">
          <Select
            value={streamTypeOptions.find((o) => o.value === (options.streamType || 'hls'))}
            options={streamTypeOptions}
            onChange={(v) => onOptionsChange({ ...options, streamType: v.value })}
            width={30}
          />
        </Field>

        <Field label="Quality" description="Stream quality (if multiple qualities are available)">
          <Select
            value={qualityOptions.find((o) => o.value === (options.quality || 'auto'))}
            options={qualityOptions}
            onChange={(v) => onOptionsChange({ ...options, quality: v.value })}
            width={30}
          />
        </Field>
      </div>

      <div className="section gf-form-group">
        <h5>Authentication</h5>

        <Field label="Username" description="Username for stream authentication">
          <Input
            value={options.username || ''}
            onChange={(e) => onOptionsChange({ ...options, username: e.currentTarget.value })}
            placeholder="username"
            width={30}
          />
        </Field>

        <Field label="Password" description="Password for stream authentication">
          <Input
            type="password"
            value={options.password || ''}
            onChange={(e) => onOptionsChange({ ...options, password: e.currentTarget.value })}
            placeholder="••••••••"
            width={30}
          />
        </Field>

        <Field label="Use Authentication" description="Enable authentication for the stream">
          <InlineSwitch
            value={options.useAuth || false}
            onChange={(e) => onOptionsChange({ ...options, useAuth: e.currentTarget.checked })}
          />
        </Field>
      </div>

      <div className="section gf-form-group">
        <h5>Player Settings</h5>

        <Field label="Show Controls" description="Show playback controls">
          <InlineSwitch
            value={options.showControls !== false}
            onChange={(e) => onOptionsChange({ ...options, showControls: e.currentTarget.checked })}
          />
        </Field>

        <Field label="Auto Play" description="Automatically start playing the stream">
          <InlineSwitch
            value={options.autoPlay !== false}
            onChange={(e) => onOptionsChange({ ...options, autoPlay: e.currentTarget.checked })}
          />
        </Field>

        <Field label="Muted" description="Mute audio by default">
          <InlineSwitch
            value={options.muted || true}
            onChange={(e) => onOptionsChange({ ...options, muted: e.currentTarget.checked })}
          />
        </Field>

        <Field label="Max Width (px)" description="Maximum width of the video player (0 for auto)">
          <Input
            type="number"
            value={options.maxWidth || 0}
            onChange={(e) => onOptionsChange({ ...options, maxWidth: parseInt(e.currentTarget.value, 10) || 0 })}
            min={0}
            width={20}
          />
        </Field>
      </div>

      <div className="section gf-form-group">
        <h5>Advanced</h5>

        <Field label="Debug Mode" description="Show debug information">
          <InlineSwitch
            value={options.debug || false}
            onChange={(e) => onOptionsChange({ ...options, debug: e.currentTarget.checked })}
          />
        </Field>

        <Field
          label="Custom CSS"
          description="Custom CSS to style the video player"
          disabled={!options.debug}
        >
          <Input
            as="textarea"
            value={options.customCss || ''}
            onChange={(e) => onOptionsChange({ ...options, customCss: e.currentTarget.value })}
            rows={3}
            disabled={!options.debug}
          />
        </Field>
      </div>
    </div>
  );
};

export default PanelOptions;
