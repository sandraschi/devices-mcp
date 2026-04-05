# Robotics Interface & Virtual Spawn Protocol

## Overview
The "Make New Virtual Robot" button in the dashboard is an interface to the **Robotics MCP orchestration layer**. It allows for the instantiation of virtual robot "digital twins" (e.g., Moorebot Scout, Unitree Go2) in a connected simulation environment before physical deployment.

## Architecture
The button triggers a POST request to `/api/robots/create_vbot`, which orchestrates the following:

1.  **Orchestration**: Signals the `robotics-mcp` server.
2.  **Target Environment**:
    - **Unity3D**: Spawns the robot prefab in the active scene.
    - **VRChat**: Triggers an OSC event to spawn the robot avatar/object.
3.  **Physical Hardware**: **NO** physical hardware is deployed by this button.

## Virtual Robots
Supported models for virtual instantiation:
- **Moorebot Scout**: Exploring patrol logic in confined spaces (under furniture).
- **Unitree Go2**: Testing quadruped locomotion and LiDAR mapping.
- **Unitree G1**: Humanoid interaction testing.

## Chinese Robot Vacuum Alternatives

Following the Roomba bankruptcy and competition from Chinese manufacturers, several excellent Chinese robot vacuum brands offer superior developer support and APIs compared to traditional Western brands. These manufacturers actively support the FOSS community, similar to how Pilot LBS supports the Moorebot Scout.

### 🏆 Dreame - Best FOSS Community Support

**FOSS-Friendly Approach**: Full open source Home Assistant integration with comprehensive API support.

- **GitHub**: `Tasshack/dreame-vacuum` (1.7k+ stars)
- **Features**: Live map support, room cleaning entities, auto-empty stations
- **Supported Models**: L10 Pro, X10, W10, D9, D10 Plus series (40+ models)
- **API Quality**: Complete device control with persistent notifications and error reporting
- **Austria Availability**: Widely available on Amazon.at (€150-400)

### 🥈 Roborock - Premium with Excellent APIs

**Developer Resources**: Modern Python library with full device control and map data access.

- **GitHub**: `Python-roborock/python-roborock` (172+ stars)
- **Features**: Local/cloud API support, advanced cleaning features, map data
- **Supported Models**: S8, Q5, Q8, Q Revo, S7, S6 series
- **API Quality**: Async Python API with comprehensive device capabilities
- **Austria Availability**: Very popular on Amazon.at (€200-600)

### 🥉 Xiaomi/Mijia - Most Mature Ecosystem

**Established Support**: Most mature and widely-used library for Xiaomi device control.

- **GitHub**: `rytilahti/python-miio` (4.2k+ stars)
- **Features**: Universal Xiaomi device control, CLI tools, comprehensive APIs
- **Supported Models**: All Xiaomi robot vacuums including Viomi series
- **API Quality**: Battle-tested with extensive device database and community support
- **Austria Availability**: Various models available (€150-300)

### 🏅 Ecovacs/Deebot - Node.js Focused

**Modern JavaScript Support**: Node.js library with full API coverage and TypeScript support.

- **GitHub**: `mrbungle64/ecovacs-deebot.js` (136+ stars)
- **Features**: Node.js/TypeScript, Docker support, comprehensive device control
- **Supported Models**: T8, T9, T10, X1, OZMO series
- **API Quality**: Modern async APIs with excellent documentation
- **Austria Availability**: T8 AIVI, X1 Turbo, T20 series (€300-500)

### Why Chinese Brands Beat Roomba

1. **Open APIs**: Full developer access vs Roomba's closed ecosystem
2. **Active Communities**: Large GitHub communities with regular updates
3. **Cross-Platform**: Work with Home Assistant, custom scripts, and automation systems
4. **Better Value**: Same or superior features at significantly lower prices
5. **Modern Features**: LIDAR mapping, app control, auto-empty stations, mopping capabilities

### Integration with devices-mcp

These robot vacuums can be integrated into the devices-mcp system via:
- **Home Assistant**: Direct integration through the above libraries
- **MQTT**: Most support MQTT for real-time status updates
- **REST APIs**: Full REST API access for custom integrations
- **WebSocket**: Real-time event streaming capabilities

## Chinese Telescope Manufacturers: FOSS Astronomy

The astronomy world follows a similar pattern to robotics - Chinese manufacturers like **Sky-Watcher** have revolutionized telescope accessibility while maintaining strong FOSS compatibility through INDI (Instrument Neutral Distributed Interface) and other open protocols.

### Sky-Watcher: Shenzhen's Astronomy Champion

**Company Profile:**
- Chinese manufacturer (headquartered in China)
- World's largest telescope manufacturer by volume
- Affordable GoTo mounts and complete telescopes
- Strong FOSS community support

**FOSS Compatibility:**
- ✅ Full INDI (Instrument Neutral Distributed Interface) support
- ✅ Linux native drivers via INDI ecosystem
- ✅ Compatible with KStars, Stellarium, PHD2 (all FOSS)
- ✅ LX200 protocol support for broad software compatibility
- ✅ ASCOM drivers for Windows astronomy software

**Beginner GoTo Setup (~€600-800):**
- Sky-Watcher 6" f/8 Newtonian optical tube (€300-400)
- AZ-GTi GoTo alt-azimuth mount (€300-400)
- Complete setup with FOSS control software

**Where to Buy in Austria:**
- **Conrad.at** - Electronics retailer with astronomy section
- **Amazon.de** (.at shipping available) - Wide selection
- **European astronomy dealers** - Teleskop-Express, Astronomik
- **Direct from Sky-Watcher Europe** - skywatcher.eu

**Creative Applications Beyond Astronomy:**
- Nature photography (eagle nests, wildlife)
- Security monitoring (long-range observation)
- Educational microscopy (with appropriate adapters)
- Landscape/time-lapse photography
- **Urban astronomy** in light-polluted cities like Vienna
- **Environmental monitoring** (avalanche, rockfall surveillance)
- **Wildlife conservation** (automated camera traps)

**Urban Astronomy Setup (Vienna Example):**
For light-polluted urban environments like Vienna's Friedensbrücke:

**Digital Imaging Solution:**
- **USB eyepiece cameras** instead of traditional eyepieces
- **Computer control** for precise focusing and capture
- **INDI software ecosystem** for robotic operation
- **Roof-mounted installation** for better sky access

**Recommended USB Cameras:**
- **ZWO ASI224MC** (€200-250) - Color CMOS for planetary imaging
- **ZWO ASI120MM Mini** (€150-200) - Monochrome for lunar/solar work
- **Celestron NexImage 5** (€100-150) - Entry-level 5MP CMOS

**Software Stack:**
- **INDI server** - Universal astronomy device control
- **KStars** - Telescope control and planning
- **SharpCap/FireCapture** - Image capture and processing
- **PHD2** - Autoguiding for long exposures

**Vienna-Specific Applications:**
- **Moon observation** (always visible despite light pollution)
- **Bright planets** (Venus, Jupiter, Mars)
- **Meteor showers** and astronomical events
- **Daytime solar observing** (with proper filters)
- **Urban stargazing tours** and educational programs

**Business Opportunities:**
- **Alpenverein partnerships** for urban astronomy programs
- **School workshops** teaching astronomy in light-polluted areas
- **Corporate team-building** events
- **Automated sky monitoring** services

**Integration with Robotics:**
The computerized GoTo mounts use similar control systems to robot navigation, creating interesting crossover possibilities between astronomy and mobile robotics platforms. The stepper motors, encoders, and PID control algorithms in GoTo mounts are directly analogous to robotic positioning systems.

> [!NOTE]
> This feature requires the `robotics-mcp` and `unity3d-mcp` servers to be active and connected. If disconnected, the button will log an error but fail gracefully.
