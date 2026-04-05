# Monitoring Stack Deployment Guide

## Overview

This guide covers deploying a comprehensive monitoring stack for MCP servers in production environments, including logging, metrics, error tracking, and performance monitoring.

## Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   MCP Servers   │───▶│  Log Aggregator │───▶│   Log Storage   │
│                 │    │   (Fluentd)      │    │  (Elasticsearch)│
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Metrics       │───▶│  Metrics Store  │───▶│   Visualization │
│  (Prometheus)   │    │  (Prometheus)   │    │   (Grafana)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Error         │───▶│  Error Tracking │───▶│   Alerting      │
│  Tracking       │    │   (Sentry)      │    │  (AlertManager) │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Components

### 1. Logging Stack (ELK)

- **Elasticsearch**: Log storage and search
- **Logstash**: Log processing and transformation
- **Kibana**: Log visualization and analysis
- **Fluentd**: Log collection and forwarding

### 2. Metrics Stack

- **Prometheus**: Metrics collection and storage
- **Grafana**: Metrics visualization and dashboards
- **AlertManager**: Alert routing and notification

### 3. Error Tracking

- **Sentry**: Error tracking and performance monitoring
- **Custom Error Handlers**: Application-specific error handling

## Docker Compose Setup

### Complete Monitoring Stack

**docker-compose.monitoring.yml**:
```yaml
version: '3.8'

services:
  # Elasticsearch
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.8.0
    container_name: monitoring-elasticsearch
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
    ports:
      - "9200:9200"
    volumes:
      - elasticsearch_data:/usr/share/elasticsearch/data
    networks:
      - monitoring

  # Logstash
  logstash:
    image: docker.elastic.co/logstash/logstash:8.8.0
    container_name: monitoring-logstash
    volumes:
      - ./config/logstash.conf:/usr/share/logstash/pipeline/logstash.conf
      - ./config/logstash.yml:/usr/share/logstash/config/logstash.yml
    ports:
      - "5044:5044"
      - "9600:9600"
    depends_on:
      - elasticsearch
    networks:
      - monitoring

  # Kibana
  kibana:
    image: docker.elastic.co/kibana/kibana:8.8.0
    container_name: monitoring-kibana
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
    ports:
      - "5601:5601"
    depends_on:
      - elasticsearch
    networks:
      - monitoring

  # Prometheus
  prometheus:
    image: prom/prometheus:latest
    container_name: monitoring-prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--web.enable-lifecycle'
    ports:
      - "9090:9090"
    volumes:
      - ./config/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    networks:
      - monitoring

  # Grafana
  grafana:
    image: grafana/grafana:latest
    container_name: monitoring-grafana
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    ports:
      - "3000:3000"
    volumes:
      - grafana_data:/var/lib/grafana
      - ./config/grafana/provisioning:/etc/grafana/provisioning
    depends_on:
      - prometheus
    networks:
      - monitoring

  # AlertManager
  alertmanager:
    image: prom/alertmanager:latest
    container_name: monitoring-alertmanager
    ports:
      - "9093:9093"
    volumes:
      - ./config/alertmanager.yml:/etc/alertmanager/alertmanager.yml
      - alertmanager_data:/alertmanager
    networks:
      - monitoring

  # Fluentd
  fluentd:
    image: fluent/fluentd:v1.16-debian-1
    container_name: monitoring-fluentd
    volumes:
      - ./config/fluentd.conf:/fluentd/etc/fluent.conf
      - ./logs:/var/log/fluentd
    ports:
      - "24224:24224"
      - "24224:24224/udp"
    depends_on:
      - elasticsearch
    networks:
      - monitoring

volumes:
  elasticsearch_data:
  prometheus_data:
  grafana_data:
  alertmanager_data:

networks:
  monitoring:
    driver: bridge
```

## Configuration Files

### 1. Logstash Configuration

**config/logstash.conf**:
```ruby
input {
  beats {
    port => 5044
  }
  tcp {
    port => 5000
    codec => json_lines
  }
}

filter {
  if [fields][service] == "mcp-server" {
    grok {
      match => { "message" => "%{TIMESTAMP_ISO8601:timestamp} - %{WORD:logger} - %{LOGLEVEL:level} - %{GREEDYDATA:message}" }
    }

    date {
      match => [ "timestamp", "ISO8601" ]
    }

    mutate {
      add_field => { "service_type" => "mcp-server" }
    }
  }
}

output {
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "mcp-logs-%{+YYYY.MM.dd}"
  }
}
```

### 2. Prometheus Configuration

**config/prometheus.yml**:
```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "rules/*.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'mcp-servers'
    static_configs:
      - targets: ['mcp-server:8000']
    metrics_path: '/metrics'
    scrape_interval: 5s

  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node-exporter:9100']
```

### 3. AlertManager Configuration

**config/alertmanager.yml**:
```yaml
global:
  smtp_smarthost: 'localhost:587'
  smtp_from: 'alerts@yourcompany.com'

route:
  group_by: ['alertname']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'web.hook'

receivers:
- name: 'web.hook'
  webhook_configs:
  - url: 'http://localhost:5001/'

- name: 'email'
  email_configs:
  - to: 'admin@yourcompany.com'
    subject: 'MCP Server Alert: {{ .GroupLabels.alertname }}'
    body: |
      {{ range .Alerts }}
      Alert: {{ .Annotations.summary }}
      Description: {{ .Annotations.description }}
      {{ end }}
```

## MCP Server Integration

### 1. Prometheus Metrics

**metrics.py**:
```python
from prometheus_client import Counter, Histogram, Gauge, start_http_server
import time
import logging

# Metrics
REQUEST_COUNT = Counter('mcp_requests_total', 'Total MCP requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('mcp_request_duration_seconds', 'MCP request duration', ['method', 'endpoint'])
ACTIVE_CONNECTIONS = Gauge('mcp_active_connections', 'Active MCP connections')
ERROR_COUNT = Counter('mcp_errors_total', 'Total MCP errors', ['error_type'])

logger = logging.getLogger(__name__)

def setup_metrics(port=8000):
    """Setup Prometheus metrics endpoint"""
    start_http_server(port)
    logger.info(f"Metrics server started on port {port}")

def track_request(method, endpoint, status_code, duration):
    """Track request metrics"""
    REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=status_code).inc()
    REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(duration)

def track_error(error_type):
    """Track error metrics"""
    ERROR_COUNT.labels(error_type=error_type).inc()
```

### 2. Structured Logging

**logging_config.py**:
```python
import logging
import json
import sys
from datetime import datetime

class StructuredFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "service": "mcp-server"
        }

        if hasattr(record, 'request_id'):
            log_entry['request_id'] = record.request_id

        if hasattr(record, 'user_id'):
            log_entry['user_id'] = record.user_id

        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry)

def setup_logging():
    """Setup structured logging for MCP server"""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredFormatter())

    logger = logging.getLogger()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    return logger
```

### 3. Error Tracking with Sentry

**error_tracking.py**:
```python
import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.fastapi import FastApiIntegration

def setup_sentry(dsn: str, environment: str = "production"):
    """Setup Sentry error tracking"""
    sentry_logging = LoggingIntegration(
        level=logging.INFO,
        event_level=logging.ERROR
    )

    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        integrations=[
            sentry_logging,
            FastApiIntegration(),
        ],
        traces_sample_rate=0.1,
        send_default_pii=False
    )

def track_error(error: Exception, context: dict = None):
    """Track error with context"""
    with sentry_sdk.push_scope() as scope:
        if context:
            for key, value in context.items():
                scope.set_extra(key, value)
        sentry_sdk.capture_exception(error)
```

### 4. Health Checks

**health.py**:
```python
import asyncio
import aiohttp
import psutil
import os
from typing import Dict, Any

class HealthChecker:
    def __init__(self):
        self.checks = {}

    async def check_database(self) -> Dict[str, Any]:
        """Check database connectivity"""
        try:
            # Add your database check here
            return {"status": "healthy", "response_time": 0.001}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

    async def check_external_api(self) -> Dict[str, Any]:
        """Check external API connectivity"""
        try:
            async with aiohttp.ClientSession() as session:
                start_time = time.time()
                async with session.get("https://api.example.com/health", timeout=5) as response:
                    response_time = time.time() - start_time
                    if response.status == 200:
                        return {"status": "healthy", "response_time": response_time}
                    else:
                        return {"status": "unhealthy", "status_code": response.status}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

    def check_system_resources(self) -> Dict[str, Any]:
        """Check system resource usage"""
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()

        return {
            "status": "healthy",
            "memory_usage": {
                "rss": memory_info.rss / 1024 / 1024,  # MB
                "vms": memory_info.vms / 1024 / 1024,  # MB
                "percent": process.memory_percent()
            },
            "cpu_percent": process.cpu_percent()
        }

    async def run_all_checks(self) -> Dict[str, Any]:
        """Run all health checks"""
        checks = {
            "database": await self.check_database(),
            "external_api": await self.check_external_api(),
            "system_resources": self.check_system_resources()
        }

        overall_status = "healthy"
        for check_name, result in checks.items():
            if result.get("status") != "healthy":
                overall_status = "unhealthy"
                break

        return {
            "status": overall_status,
            "checks": checks,
            "timestamp": datetime.utcnow().isoformat()
        }
```

## Grafana Dashboards

### 1. MCP Server Dashboard

**config/grafana/provisioning/dashboards/mcp-dashboard.json**:
```json
{
  "dashboard": {
    "title": "MCP Server Dashboard",
    "panels": [
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(mcp_requests_total[5m])",
            "legendFormat": "{{method}} {{endpoint}}"
          }
        ]
      },
      {
        "title": "Response Time",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(mcp_request_duration_seconds_bucket[5m]))",
            "legendFormat": "95th percentile"
          }
        ]
      },
      {
        "title": "Error Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(mcp_errors_total[5m])",
            "legendFormat": "{{error_type}}"
          }
        ]
      },
      {
        "title": "Active Connections",
        "type": "singlestat",
        "targets": [
          {
            "expr": "mcp_active_connections"
          }
        ]
      }
    ]
  }
}
```

## Alerting Rules

### 1. Prometheus Alert Rules

**config/rules/mcp-alerts.yml**:
```yaml
groups:
- name: mcp-server
  rules:
  - alert: HighErrorRate
    expr: rate(mcp_errors_total[5m]) > 0.1
    for: 2m
    labels:
      severity: warning
    annotations:
      summary: "High error rate detected"
      description: "MCP server error rate is {{ $value }} errors per second"

  - alert: HighResponseTime
    expr: histogram_quantile(0.95, rate(mcp_request_duration_seconds_bucket[5m])) > 1
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High response time detected"
      description: "95th percentile response time is {{ $value }} seconds"

  - alert: ServerDown
    expr: up == 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "MCP server is down"
      description: "MCP server has been down for more than 1 minute"

  - alert: HighMemoryUsage
    expr: process_resident_memory_bytes / 1024 / 1024 > 512
    for: 5m
        labels:
      severity: warning
    annotations:
      summary: "High memory usage"
      description: "MCP server memory usage is {{ $value }} MB"
```

## Deployment Scripts

### 1. Setup Script

**scripts/setup-monitoring.sh**:
```bash
#!/bin/bash

# Create necessary directories
mkdir -p config/{logstash,grafana/provisioning/{datasources,dashboards},rules}
mkdir -p logs

# Set permissions
chmod 755 config
chmod 644 config/*.yml
chmod 644 config/*.conf

# Create Docker network
docker network create monitoring

# Start monitoring stack
docker-compose -f docker-compose.monitoring.yml up -d

# Wait for services to be ready
echo "Waiting for services to start..."
sleep 30

# Check service health
echo "Checking service health..."
curl -f http://localhost:9200/_cluster/health || echo "Elasticsearch not ready"
curl -f http://localhost:9090/-/healthy || echo "Prometheus not ready"
curl -f http://localhost:3000/api/health || echo "Grafana not ready"

echo "Monitoring stack setup complete!"
echo "Access URLs:"
echo "  Kibana: http://localhost:5601"
echo "  Grafana: http://localhost:3000 (admin/admin)"
echo "  Prometheus: http://localhost:9090"
echo "  AlertManager: http://localhost:9093"
```

### 2. MCP Server Integration

**scripts/integrate-mcp-server.sh**:
```bash
#!/bin/bash

# Add MCP server to monitoring network
docker network connect monitoring your-mcp-server

# Update MCP server configuration
cat >> mcp-server.env << EOF
# Monitoring configuration
PROMETHEUS_ENABLED=true
PROMETHEUS_PORT=8000
SENTRY_DSN=your-sentry-dsn
LOG_LEVEL=INFO
LOG_FORMAT=json
EOF

# Restart MCP server with monitoring
docker-compose restart mcp-server
```

## Best Practices

### 1. Log Management

- Use structured logging with consistent fields
- Implement log rotation to prevent disk space issues
- Set appropriate log levels for different environments
- Include correlation IDs for request tracing

### 2. Metrics Collection

- Collect business metrics, not just technical metrics
- Use appropriate metric types (Counter, Histogram, Gauge)
- Set up proper labeling for effective querying
- Monitor resource usage and performance

### 3. Alerting

- Set up alerts for critical issues only
- Use appropriate alert thresholds
- Implement alert escalation procedures
- Test alerting mechanisms regularly

### 4. Security

- Secure monitoring endpoints with authentication
- Use TLS for communication between components
- Implement proper access controls
- Regular security updates

### 5. Maintenance

- Regular backup of monitoring data
- Monitor monitoring stack health
- Plan for capacity scaling
- Regular cleanup of old data

## Troubleshooting

### Common Issues

1. **Elasticsearch Out of Memory**
   - Increase heap size
   - Optimize index settings
   - Implement index lifecycle management

2. **Prometheus Storage Issues**
   - Configure retention policies
   - Use external storage for long-term retention
   - Monitor disk usage

3. **Grafana Performance**
   - Optimize dashboard queries
   - Use appropriate refresh intervals
   - Implement dashboard caching

4. **Log Processing Delays**
   - Scale Logstash instances
   - Optimize log parsing patterns
   - Use appropriate buffer settings

This monitoring stack provides comprehensive observability for MCP servers in production environments, enabling proactive issue detection and resolution.
