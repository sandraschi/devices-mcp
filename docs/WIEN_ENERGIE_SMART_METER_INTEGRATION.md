# ⚡ Wien Energie Smart Meter Integration

**Project**: Home Security MCP Platform
**Status**: Implementation Phase
**Date**: November 21, 2025

---

## 🎯 **OVERVIEW**

Integration of Wien Energie smart meters (via Wiener Netze infrastructure) into the Home Security MCP Platform for comprehensive whole-house energy monitoring.

### **Key Features**
- **Real-time Energy Consumption**: Live power consumption data from smart meter
- **Historical Data**: Daily, monthly, and annual energy usage tracking
- **Cost Analysis**: Energy cost calculation based on Wien Energie tariffs
- **Dashboard Integration**: Unified energy monitoring with Tapo P115 smart plugs
- **MCP Tools**: AI-powered energy monitoring and analysis

---

## 📋 **REQUIREMENTS**

### **Hardware Requirements**
1. **Smart Meter**: Wien Energie smart meter installed by Wiener Netze
2. **Infrared Reading Adapter**: IEC 62056-21 compliant adapter
   - Examples: IR adapter from third-party vendors
   - Must support DLMS/COSEM protocol
   - USB or serial connection to computer/integration device

### **Software Requirements**
1. **Customer Interface Activation**:
   - Activate via [Wiener Netze Smart Meter Portal](https://www.wienernetze.at/en/smart-meter-webportal)
   - Navigate to "Anlagendaten" → Select meter → "Bearbeiten" → Enable customer interface
2. **Security Key**: Obtain from Wiener Netze portal (required for data decryption)
3. **Python Libraries**:
   - `dlms-cosem` or similar DLMS/COSEM protocol library
   - Serial/USB communication library (`pyserial`)

---

## 🔧 **TECHNICAL IMPLEMENTATION**

### **Protocol Details**
- **Standard**: IEC 62056-21 (DLMS/COSEM)
- **Communication**: Infrared (IR) via customer interface
- **Data Format**: DLMS/COSEM OBIS codes
- **Security**: AES-128 encryption with security key
- **Update Frequency**: Real-time or periodic polling (configurable)

### **Data Points Available**
- **Total Energy Consumption** (kWh): OBIS code 1.0.0.0.0.255
- **Active Power** (W): OBIS code 1.0.1.7.0.255
- **Voltage** (V): OBIS code 1.0.32.7.0.255
- **Current** (A): OBIS code 1.0.31.7.0.255
- **Power Factor**: OBIS code 1.0.13.7.0.255
- **Frequency** (Hz): OBIS code 1.0.14.7.0.255

---

## 📁 **FILE STRUCTURE**

```
src/devices_mcp/
├── ingest/
│   ├── __init__.py                    # Export WienEnergieIngestionService
│   └── wien_energie.py                # Smart meter ingestion service
├── tools/
│   └── energy/
│       └── smart_meter_tools.py       # MCP tools for smart meter
└── web/
    └── api/
        └── energy.py                  # API endpoints (extend existing)
```

---

## ⚙️ **CONFIGURATION**

### **config.yaml Structure**

```yaml
energy:
  wien_energie:
    enabled: true
    adapter:
      type: "ir"  # or "serial", "usb"
      port: "/dev/ttyUSB0"  # or COM port on Windows
      baudrate: 9600
      timeout: 5
    security:
      key: "your_security_key_from_wiener_netze"  # From portal
      encryption: "AES-128"
    meter:
      serial_number: "auto-detect"  # or manual entry
      obis_codes:
        total_energy: "1.0.0.0.0.255"
        active_power: "1.0.1.7.0.255"
        voltage: "1.0.32.7.0.255"
        current: "1.0.31.7.0.255"
    polling:
      enabled: true
      interval_seconds: 60  # Poll every minute
    tariffs:
      base_rate: 0.12  # EUR per kWh (update with actual Wien Energie rate)
      peak_rate: 0.15  # Peak hours (if applicable)
      off_peak_rate: 0.10  # Off-peak hours (if applicable)
```

### **Environment Variables** (Alternative)

```bash
WIEN_ENERGIE_ENABLED=true
WIEN_ENERGIE_ADAPTER_PORT=/dev/ttyUSB0
WIEN_ENERGIE_SECURITY_KEY=your_key_here
WIEN_ENERGIE_POLLING_INTERVAL=60
```

---

## 🔌 **INTEGRATION POINTS**

### **1. Ingestion Service**
- **File**: `src/devices_mcp/ingest/wien_energie.py`
- **Class**: `WienEnergieIngestionService`
- **Methods**:
  - `discover_meter()`: Detect and connect to smart meter
  - `fetch_current_reading()`: Get real-time energy data
  - `fetch_historical_data()`: Retrieve historical consumption
  - `get_tariff_info()`: Get current tariff rates

### **2. MCP Tools**
- **File**: `src/devices_mcp/tools/energy/smart_meter_tools.py`
- **Tools**:
  - `get_smart_meter_status`: Current meter status and readings
  - `get_energy_consumption`: Energy consumption data (daily/monthly)
  - `get_power_consumption`: Real-time power consumption
  - `calculate_energy_cost`: Cost calculation based on tariffs
  - `get_historical_usage`: Historical usage patterns

### **3. API Endpoints**
- **File**: `src/devices_mcp/web/api/energy.py` (extend existing)
- **Endpoints**:
  - `GET /api/energy/smart-meter/status`: Current meter status
  - `GET /api/energy/smart-meter/current`: Real-time readings
  - `GET /api/energy/smart-meter/history`: Historical data
  - `GET /api/energy/smart-meter/cost`: Cost analysis

### **4. Dashboard Integration**
- **File**: `src/devices_mcp/web/templates/energy.html` (extend existing)
- **Features**:
  - Smart meter data display alongside Tapo P115 plugs
  - Real-time power consumption chart
  - Daily/monthly energy comparison
  - Cost tracking and projections

---

## 🚀 **IMPLEMENTATION PHASES**

### **Phase 1: Core Ingestion Service** ✅ (In Progress)
- [x] Create `WienEnergieIngestionService` class
- [ ] Implement DLMS/COSEM protocol communication
- [ ] Add security key handling and decryption
- [ ] Implement OBIS code reading
- [ ] Add error handling and retry logic

### **Phase 2: Configuration & Setup**
- [ ] Add configuration structure to `config.yaml`
- [ ] Create setup documentation
- [ ] Add validation for adapter and security key
- [ ] Implement adapter auto-detection

### **Phase 3: MCP Tools**
- [ ] Create smart meter MCP tools
- [ ] Add tool registration to server
- [ ] Implement tool error handling
- [ ] Add tool documentation

### **Phase 4: API & Dashboard**
- [ ] Extend energy API endpoints
- [ ] Update energy dashboard UI
- [ ] Add smart meter data visualization
- [ ] Implement cost tracking display

### **Phase 5: Testing & Documentation**
- [ ] Unit tests for ingestion service
- [ ] Integration tests with mock adapter
- [ ] User documentation
- [ ] Troubleshooting guide

---

## 📚 **REFERENCES**

### **Wiener Netze Resources**
- [Smart Meter Customer Interface](https://www.wienernetze.at/en/smart-meter-kundenschnittstelle)
- [Smart Meter Webportal](https://www.wienernetze.at/en/smart-meter-webportal)
- [Smart Meter Business Portal](https://www.wienernetze.at/en/smart-meter-businessportal)

### **Technical Standards**
- **IEC 62056-21**: Electricity metering data exchange - Direct local data exchange
- **DLMS/COSEM**: Device Language Message Specification / Companion Specification for Energy Metering
- **OBIS Codes**: Object Identification System codes for energy data

### **Python Libraries**
- `dlms-cosem`: DLMS/COSEM protocol implementation (if available)
- `pyserial`: Serial port communication
- `pyserial-asyncio`: Async serial communication

---

## ⚠️ **LIMITATIONS & CONSIDERATIONS**

1. **Hardware Dependency**: Requires physical IR adapter connection
2. **Security Key Management**: Security key must be kept secure
3. **Polling Frequency**: Respect smart meter rate limits
4. **Data Storage**: Historical data storage requirements
5. **Network Dependency**: Adapter must be physically connected to integration device

---

## 🔐 **SECURITY NOTES**

- **Security Key**: Store securely, never commit to version control
- **Encryption**: All communication uses AES-128 encryption
- **Access Control**: Limit access to smart meter data
- **Audit Logging**: Log all smart meter access attempts

---

**Status**: ✅ Core Implementation Complete
**Last Updated**: November 21, 2025

---

## ✅ **IMPLEMENTATION STATUS**

### **Completed Components**
- ✅ **Ingestion Service**: `WienEnergieIngestionService` with DLMS/COSEM protocol structure
- ✅ **Configuration**: Complete `config.yaml` setup with adapter, security, and tariff settings
- ✅ **MCP Tools**: Three smart meter tools (`smart_meter_status`, `smart_meter_consumption`, `smart_meter_cost`)
- ✅ **API Endpoints**: Full REST API for smart meter data (`/api/energy/smart-meter/*`)
- ✅ **Dependencies**: Added `pyserial` and `pyserial-asyncio` to requirements
- ✅ **Documentation**: Complete integration guide

### **Remaining Work**
- ⚠️ **DLMS/COSEM Protocol**: Actual protocol implementation (currently placeholder)
- ⚠️ **Dashboard UI**: Frontend integration for smart meter display
- ⚠️ **Testing**: Unit and integration tests with real adapter

### **Next Steps**
1. Connect IR adapter and test serial communication
2. Implement DLMS/COSEM protocol using library or custom implementation
3. Update energy dashboard UI to display smart meter data
4. Add comprehensive error handling and retry logic
