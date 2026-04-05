# Grafana P115 Power Spike Alerting Setup

## Overview

This guide explains how to set up Grafana alerts for Tapo P115 smart plug power consumption spikes. This is useful for detecting heating cycles (e.g., Zojirushi hot water dispenser) when power jumps from low standby to high heating power (>500W).

## Prerequisites

1. Grafana instance running
2. Prometheus configured and scraping `/metrics` endpoint
3. Tapo P115 plugs configured and accessible

## Setup Steps

### 1. Verify Metrics Endpoint

The Prometheus metrics endpoint is available at:
```
http://localhost:7777/metrics
```

Test it:
```bash
curl http://localhost:7777/metrics | grep tapo_p115_power_watts
```

You should see metrics like:
```
tapo_p115_power_watts{device_id="tapo_p115_kitchen_zojirushi",host="192.168.0.17",name="Kitchen Zojirushi",location="Kitchen"} 0.0
```

### 2. Configure Prometheus to Scrape Metrics

Add to `prometheus.yml`:
```yaml
scrape_configs:
  - job_name: 'devices-mcp'
    scrape_interval: 30s
    static_configs:
      - targets: ['localhost:7777']
```

### 3. Import Alert Rules

The alert rules are in `grafana/provisioning/alerting/p115-power-spike-alerts.yaml`.

**For Grafana 8.x+ (unified alerting):**
- Copy the file to Grafana's alerting provisioning directory
- Restart Grafana
- Alerts will appear in Grafana UI under "Alerting" → "Alert rules"

**For older Grafana:**
- Use Prometheus Alertmanager instead
- Convert the rules to Prometheus alert rules format

### 4. Alert Rules Included

#### Power Spike (>500W)
- **Trigger**: Power > 500W for 10 seconds
- **Severity**: Warning
- **Use Case**: Detects heating cycles on hot water dispensers

#### Power Surge (>800W)
- **Trigger**: Power > 800W for 5 seconds
- **Severity**: Critical
- **Use Case**: Detects unusually high power consumption (potential issue)

#### Rapid Power Change
- **Trigger**: Power jumps from <10W to >500W within 30 seconds
- **Severity**: Info
- **Use Case**: Detects heating cycle start (normal operation)

### 5. Configure Notifications

#### Browser Sound Alert

The notification channel is configured in `grafana/provisioning/notifiers/sound-alert.yaml`.

For browser-based sound alerts:
1. Configure a webhook notification channel in Grafana
2. Point it to your webhook endpoint (e.g., `http://localhost:7777/api/alerts/webhook`)
3. In your dashboard, use browser notification API to trigger sound

#### Alternative: Email/Slack

Update `grafana/provisioning/notifiers/sound-alert.yaml` with your email/Slack webhook.

### 6. Test the Alerts

1. Turn on your Zojirushi hot water dispenser
2. Wait for heating cycle (power should spike to 500W+)
3. Check Grafana alerts - you should see "P115 Power Spike Detected"
4. If configured, you should hear a browser notification sound

### 7. Dashboard Integration

The alert rules are automatically displayed in the "Sensor Overview" dashboard under "Alerting" → "Alert rules".

You can also create a dashboard panel that shows:
- Current power consumption
- Alert status
- Power history with alert thresholds marked

## Troubleshooting

### Metrics Not Appearing

1. Check `/metrics` endpoint is accessible:
   ```bash
   curl http://localhost:7777/metrics
   ```

2. Verify Prometheus is scraping:
   - Go to Prometheus UI → Status → Targets
   - Check `devices-mcp` target is UP

3. Verify metrics in Prometheus:
   - Prometheus UI → Graph
   - Query: `tapo_p115_power_watts`

### Alerts Not Triggering

1. Check alert rules are loaded:
   - Grafana UI → Alerting → Alert rules
   - Verify "tapo_p115_power_alerts" group is visible

2. Check alert evaluation:
   - Grafana UI → Alerting → Alert rules → Select rule → "Test rule"
   - Verify query returns data

3. Check notification channels:
   - Grafana UI → Alerting → Notification channels
   - Verify channel is configured and tested

### Browser Sound Not Working

1. Browser notifications must be allowed for your Grafana domain
2. Check browser console for notification API errors
3. Ensure webhook endpoint is accessible from Grafana

## Next Steps

- Customize alert thresholds for your specific devices
- Add more alert rules for different power patterns
- Integrate with home automation (e.g., turn on notifications when heating starts)
- Create custom dashboard panels for alert visualization
