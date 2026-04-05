# Containerization Guidelines for MCP Servers

## Overview

This guide covers when and how to containerize MCP servers, including best practices, trade-offs, and implementation strategies.

## When to Containerize

### ✅ Good Use Cases

1. **Complex Dependencies**
   - Multiple system packages required
   - Native libraries or binaries
   - Specific Python/Node.js versions

2. **Production Deployment**
   - Consistent environment across deployments
   - Easy scaling and orchestration
   - Integration with container orchestration (Kubernetes, Docker Swarm)

3. **Cross-Platform Compatibility**
   - Ensure consistent behavior across different OS
   - Avoid "works on my machine" issues

4. **Resource Isolation**
   - Memory and CPU limits
   - Security isolation
   - Process isolation

### ❌ Avoid Containerization When

1. **Simple Python MCP Servers**
   - Minimal dependencies
   - FastMCP-based servers
   - Local development only

2. **Claude Desktop Integration**
   - Claude Desktop expects local processes
   - STDIO communication works better with local processes
   - No network overhead

3. **Development and Testing**
   - Slower iteration cycles
   - Debugging complexity
   - Resource overhead

## Containerization Strategies

### 1. Lightweight Python Containers

**Dockerfile**:
```dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 mcpuser && chown -R mcpuser:mcpuser /app
USER mcpuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import your_mcp_server; print('OK')" || exit 1

# Default command
CMD ["python", "-m", "your_mcp_server"]
```

**requirements.txt**:
```
fastmcp>=0.1.0
pydantic>=2.0.0
aiohttp>=3.8.0
```

### 2. Multi-Stage Builds

**Dockerfile**:
```dockerfile
# Build stage
FROM python:3.11-slim as builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Runtime stage
FROM python:3.11-slim

# Copy Python packages from builder
COPY --from=builder /root/.local /root/.local

# Set working directory
WORKDIR /app

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 mcpuser && chown -R mcpuser:mcpuser /app
USER mcpuser

# Add user packages to PATH
ENV PATH=/root/.local/bin:$PATH

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import your_mcp_server; print('OK')" || exit 1

CMD ["python", "-m", "your_mcp_server"]
```

### 3. Node.js MCP Servers

**Dockerfile**:
```dockerfile
FROM node:18-alpine

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production

# Copy application code
COPY . .

# Create non-root user
RUN addgroup -g 1000 -S mcpuser && \
    adduser -u 1000 -S mcpuser -G mcpuser
RUN chown -R mcpuser:mcpuser /app
USER mcpuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD node -e "console.log('OK')" || exit 1

CMD ["node", "index.js"]
```

## Docker Compose Setup

### Basic MCP Server

**docker-compose.yml**:
```yaml
version: '3.8'

services:
  mcp-server:
    build: .
    container_name: your-mcp-server
    environment:
      - API_KEY=${API_KEY}
      - DEBUG=false
      - LOG_LEVEL=INFO
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c", "import your_mcp_server; print('OK')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

### With External Services

**docker-compose.yml**:
```yaml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    container_name: mcp-redis
    restart: unless-stopped
    volumes:
      - redis_data:/data

  mcp-server:
    build: .
    container_name: your-mcp-server
    environment:
      - API_KEY=${API_KEY}
      - REDIS_URL=redis://redis:6379
      - DEBUG=false
    depends_on:
      - redis
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c", "import your_mcp_server; print('OK')"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  redis_data:
```

## Production Considerations

### 1. Security

**Security Hardening**:
```dockerfile
FROM python:3.11-slim

# Install security updates
RUN apt-get update && apt-get install -y \
    curl \
    && apt-get upgrade -y \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 -s /bin/bash mcpuser

# Set secure permissions
RUN chmod 755 /app && chown -R mcpuser:mcpuser /app

# Switch to non-root user
USER mcpuser

# Remove unnecessary packages
RUN apt-get autoremove -y && apt-get clean
```

### 2. Resource Limits

**Resource Constraints**:
```yaml
services:
  mcp-server:
    build: .
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 256M
    restart: unless-stopped
```

### 3. Logging

**Structured Logging**:
```python
import logging
import json
import sys

# Configure container-friendly logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)  # Send to stdout for Docker
    ]
)

logger = logging.getLogger(__name__)

@mcp.tool()
def containerized_tool(param: str) -> str:
    """Tool optimized for containerized environment"""
    logger.info(f"Processing in container: {param}")
    try:
        result = process_param(param)
        logger.info(f"Container processing completed: {result}")
        return result
    except Exception as e:
        logger.error(f"Container processing failed: {e}")
        raise
```

### 4. Health Checks

**Comprehensive Health Checks**:
```python
import asyncio
import aiohttp
from fastmcp import FastMCP

mcp = FastMCP("containerized-server")

@mcp.tool()
async def health_check() -> str:
    """Comprehensive health check for containerized environment"""
    health_status = {
        "status": "healthy",
        "checks": {}
    }

    # Check database connectivity
    try:
        # Add your database check here
        health_status["checks"]["database"] = "ok"
    except Exception as e:
        health_status["checks"]["database"] = f"error: {e}"
        health_status["status"] = "unhealthy"

    # Check external API
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://api.example.com/health", timeout=5) as response:
                if response.status == 200:
                    health_status["checks"]["external_api"] = "ok"
                else:
                    health_status["checks"]["external_api"] = f"error: {response.status}"
                    health_status["status"] = "unhealthy"
    except Exception as e:
        health_status["checks"]["external_api"] = f"error: {e}"
        health_status["status"] = "unhealthy"

    return json.dumps(health_status)
```

## Kubernetes Deployment

### 1. Basic Deployment

**deployment.yaml**:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mcp-server
  labels:
    app: mcp-server
spec:
  replicas: 3
  selector:
    matchLabels:
      app: mcp-server
  template:
    metadata:
      labels:
        app: mcp-server
    spec:
      containers:
      - name: mcp-server
        image: your-registry/mcp-server:latest
        ports:
        - containerPort: 8080
        env:
        - name: API_KEY
          valueFrom:
            secretKeyRef:
              name: mcp-secrets
              key: api-key
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          exec:
            command:
            - python
            - -c
            - "import your_mcp_server; print('OK')"
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          exec:
            command:
            - python
            - -c
            - "import your_mcp_server; print('OK')"
          initialDelaySeconds: 5
          periodSeconds: 5
```

### 2. Service Configuration

**service.yaml**:
```yaml
apiVersion: v1
kind: Service
metadata:
  name: mcp-server-service
spec:
  selector:
    app: mcp-server
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8080
  type: ClusterIP
```

## Monitoring and Observability

### 1. Prometheus Metrics

**metrics.py**:
```python
from prometheus_client import Counter, Histogram, Gauge, start_http_server
import time

# Metrics
REQUEST_COUNT = Counter('mcp_requests_total', 'Total MCP requests', ['method', 'endpoint'])
REQUEST_DURATION = Histogram('mcp_request_duration_seconds', 'MCP request duration')
ACTIVE_CONNECTIONS = Gauge('mcp_active_connections', 'Active MCP connections')

def setup_metrics(port=8000):
    """Setup Prometheus metrics endpoint"""
    start_http_server(port)
    print(f"Metrics server started on port {port}")

@mcp.tool()
def monitored_tool(param: str) -> str:
    """Tool with Prometheus metrics"""
    start_time = time.time()

    try:
        REQUEST_COUNT.labels(method='tool', endpoint='monitored_tool').inc()
        result = process_param(param)

        REQUEST_DURATION.observe(time.time() - start_time)
        return result

    except Exception as e:
        REQUEST_COUNT.labels(method='tool', endpoint='monitored_tool').inc()
        REQUEST_DURATION.observe(time.time() - start_time)
        raise
```

### 2. Log Aggregation

**docker-compose.yml with ELK Stack**:
```yaml
version: '3.8'

services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.8.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
    ports:
      - "9200:9200"

  logstash:
    image: docker.elastic.co/logstash/logstash:8.8.0
    volumes:
      - ./logstash.conf:/usr/share/logstash/pipeline/logstash.conf
    depends_on:
      - elasticsearch

  kibana:
    image: docker.elastic.co/kibana/kibana:8.8.0
    ports:
      - "5601:5601"
    depends_on:
      - elasticsearch

  mcp-server:
    build: .
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
    depends_on:
      - logstash
```

## Best Practices

### 1. Image Optimization

- Use multi-stage builds to reduce image size
- Remove unnecessary packages and files
- Use specific version tags, not `latest`
- Leverage Docker layer caching

### 2. Security

- Run as non-root user
- Use minimal base images
- Keep base images updated
- Scan images for vulnerabilities

### 3. Performance

- Set appropriate resource limits
- Use health checks
- Implement graceful shutdown
- Monitor resource usage

### 4. Development

- Use Docker Compose for local development
- Mount source code as volumes for hot reloading
- Use development-specific configurations
- Test containerized builds in CI/CD

## When NOT to Containerize

### Simple MCP Servers

For simple FastMCP-based servers with minimal dependencies:

```python
# Simple MCP server - no containerization needed
from fastmcp import FastMCP

mcp = FastMCP("simple-server")

@mcp.tool()
def simple_tool(param: str) -> str:
    """Simple tool that doesn't need containerization"""
    return f"Processed: {param}"

if __name__ == "__main__":
    mcp.run()
```

### Local Development

For local development and testing:

```bash
# Simple local setup
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m your_mcp_server
```

## Conclusion

Containerization is powerful for complex MCP servers in production environments, but adds overhead for simple use cases. Evaluate your specific needs:

- **Simple FastMCP servers**: Use local processes
- **Complex dependencies**: Consider containerization
- **Production deployment**: Use containers with proper monitoring
- **Development**: Use local processes with Docker Compose for services

The key is to match the complexity of your deployment strategy to the complexity of your MCP server.
