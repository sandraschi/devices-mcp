# Tapo Camera Stream Plugin for Grafana

A Grafana panel plugin for viewing and controlling Tapo camera streams with PTZ (Pan-Tilt-Zoom) support.

## Features

- Stream video from Tapo cameras (HLS, RTSP, RTMP, WebRTC, MJPEG)
- PTZ (Pan-Tilt-Zoom) controls
- Preset positions
- Authentication support
- Stream quality selection
- Responsive design

## Installation

### Prerequisites

- Grafana 9.0.0 or later
- Node.js 16.x or later
- npm or yarn

### Docker Compose Installation (Recommended)

1. **Clone this repository** to your local machine:

   ```bash
   git clone https://github.com/your-username/devices-mcp.git
   cd devices-mcp/grafana/plugins/tapo-camera-stream
   ```

2. **Build the plugin**:

   ```bash
   npm install --legacy-peer-deps
   npm run build
   ```

3. **Create or update `docker-compose.yml`** in the project root:
   ```yaml
   version: '3.8'
   services:
     grafana:
       image: grafana/grafana:latest
       container_name: grafana-tapo
       ports:
         - "7360:3000"  # Access at http://localhost:7360
       volumes:
         - ./:/var/lib/grafana/plugins/tapo-camera-stream
       environment:
         - GF_INSTALL_PLUGINS=grafana-clock-panel,grafana-simple-json-datasource
         - GF_SECURITY_ADMIN_USER=admin
         - GF_SECURITY_ADMIN_PASSWORD=admin
       restart: unless-stopped
   ```

4. **Start the services**:
   ```bash
   docker-compose up -d
   ```

5. **Access Grafana**:
   - Open your browser to `http://localhost:7360`
   - Log in with admin/admin
   - The Tapo Camera Stream plugin should be available in your panels

### Alternative: Docker Run

If you prefer using `docker run` directly:
```bash
docker run -d \
  -p 7360:3000 \
  -v "$(pwd)":/var/lib/grafana/plugins/tapo-camera-stream \
  -e "GF_INSTALL_PLUGINS=grafana-clock-panel,grafana-simple-json-datasource" \
  -e "GF_SECURITY_ADMIN_USER=admin" \
  -e "GF_SECURITY_ADMIN_PASSWORD=admin" \
  --name=grafana-tapo \
  grafana/grafana:latest
```

## Usage

1. Add a new panel to your dashboard
2. Select "Tapo Camera Stream" as the visualization type
3. Configure the stream URL and settings in the panel options

### Stream Configuration

- **Stream URL**: The URL of your camera stream (e.g., `rtsp://camera-ip:554/stream1`)
- **Stream Type**: The protocol used by your camera (HLS, RTSP, RTMP, WebRTC, or MJPEG)
- **Authentication**: Enable if your camera requires authentication
- **Username/Password**: Credentials for camera authentication
- **Auto Play**: Start playing the stream automatically
- **Show Controls**: Show playback controls
- **Muted**: Mute audio by default
- **Max Width**: Maximum width of the video player (0 for auto)

### PTZ Controls

- Use the on-screen controls to pan, tilt, and zoom
- Save and recall preset positions
- Adjust movement speed

## Development

### Prerequisites

- Node.js 16.x or later
- Yarn or npm
- Grafana 9.0.0 or later

### Setup

1. Install dependencies:
   ```
   yarn install
   ```

2. Start the development server:
   ```
   yarn dev
   ```

3. Open Grafana in your browser and add a new panel with the Tapo Camera Stream visualization.

### Building

To build the plugin for production:

```
yarn build
```

The built plugin will be in the `dist` directory.

## License

MIT

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.

## Support

For support, please open an issue on GitHub.
