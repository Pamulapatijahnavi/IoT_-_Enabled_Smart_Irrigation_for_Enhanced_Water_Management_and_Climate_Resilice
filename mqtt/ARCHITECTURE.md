# MQTT IoT System Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           MQTT IoT Data Collection System                      │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────┐    MQTT Messages    ┌─────────────────┐    Data Storage    ┌─────────────────┐
│                 │ ──────────────────► │                 │ ──────────────────► │                 │
│  Sensor Client  │                     │  MQTT Broker    │                     │  CSV Files      │
│  (Simulator)    │                     │  (Mosquitto)    │                     │  (sensor_data)  │
│                 │                     │                 │                     │                 │
└─────────────────┘                     └─────────────────┘                     └─────────────────┘
         │                                       │                                       │
         │                                       │                                       │
         │                                       ▼                                       │
         │                              ┌─────────────────┐                              │
         │                              │                 │                              │
         │                              │ MQTT Subscriber │                              │
         │                              │   Service       │                              │
         │                              │                 │                              │
         │                              └─────────────────┘                              │
         │                                       │                                       │
         │                                       │                                       │
         │                                       ▼                                       │
         │                              ┌─────────────────┐                              │
         │                              │                 │                              │
         │                              │  Alert Service  │                              │
         │                              │  (Thresholds)   │                              │
         │                              │                 │                              │
         │                              └─────────────────┘                              │
         │                                       │                                       │
         │                                       │                                       │
         │                                       ▼                                       │
         │                              ┌─────────────────┐                              │
         │                              │                 │                              │
         │                              │ Web Dashboard   │◄─────────────────────────────┘
         │                              │ (Plotly Dash)   │
         │                              │                 │
         │                              └─────────────────┘
         │                                       │
         │                                       │
         │                                       ▼
         │                              ┌─────────────────┐
         │                              │                 │
         │                              │   Web Browser   │
         │                              │  (Real-time UI) │
         │                              │                 │
         │                              └─────────────────┘
```

## Component Details

### 1. MQTT Broker (Mosquitto)
- **Location**: `broker/mosquitto.conf`
- **Port**: 1883 (MQTT), 9001 (WebSocket)
- **Features**: 
  - Anonymous access enabled
  - Persistence enabled
  - WebSocket support for web clients

### 2. Sensor Client (Simulator)
- **Location**: `client/sensor_simulator.py`
- **Purpose**: Simulates IoT sensors sending data
- **Sensors**: Temperature, Humidity, Pressure, Light
- **Data Format**: JSON with timestamp, sensor_id, value, unit, location
- **Topics**: `sensors/temperature`, `sensors/humidity`, `sensors/pressure`, `sensors/light`

### 3. MQTT Subscriber Service
- **Location**: `backend/mqtt_subscriber.py`
- **Purpose**: Receives MQTT messages and processes them
- **Features**:
  - Subscribes to all sensor topics
  - Processes data in background threads
  - Stores data to CSV files
  - Triggers alert checks

### 4. Data Storage Service
- **Location**: `backend/data_storage.py`
- **Purpose**: Manages CSV file storage
- **Files**:
  - `data/sensor_data.csv` - All sensor readings
- **Features**:
  - Automatic CSV file creation
  - Data retrieval functions
  - Statistics and cleanup

### 5. Alert Service
- **Location**: `backend/alert_service.py`
- **Purpose**: Monitors data for threshold violations
- **Features**:
  - Configurable thresholds per sensor type
  - Alert cooldown to prevent spam
  - Severity levels (info, warning, critical)
  - Alert logging

### 6. Web Dashboard
- **Location**: `dashboard/app.py`
- **Purpose**: Real-time data visualization
- **Features**:
  - Multi-sensor overview charts
  - Individual sensor time series
  - Current value gauges
  - System status display
  - Auto-refresh every 5 seconds

## Data Flow

1. **Data Generation**: Sensor simulator generates realistic sensor data
2. **MQTT Publishing**: Data is published to MQTT broker on specific topics
3. **MQTT Subscription**: Subscriber service receives all sensor messages
4. **Data Processing**: Messages are queued and processed in background
5. **Storage**: Processed data is stored in CSV files
6. **Alerting**: Alert service checks for threshold violations
7. **Visualization**: Web dashboard reads CSV data and displays real-time charts

## MQTT Topics

| Topic | Description | Data Format |
|-------|-------------|-------------|
| `sensors/temperature` | Temperature sensor data | JSON with value, unit, location |
| `sensors/humidity` | Humidity sensor data | JSON with value, unit, location |
| `sensors/pressure` | Pressure sensor data | JSON with value, unit, location |
| `sensors/light` | Light sensor data | JSON with value, unit, location |

## JSON Message Format

### Sensor Data
```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "sensor_id": "temp_001",
  "sensor_type": "temperature",
  "value": 25.5,
  "unit": "celsius",
  "location": "room_1"
}
```


## Quick Start

1. **Setup**: Run `./setup.sh` to install dependencies
2. **Start All Services**: Run `python3 start_services.py`
3. **Access Dashboard**: Open http://localhost:8050
4. **View Data**: Check `data/sensor_data.csv` for stored data

## Individual Service Commands

```bash
# MQTT Broker only
mosquitto -c broker/mosquitto.conf

# MQTT Subscriber
cd server && python3 mqtt_subscriber.py

# Web Dashboard
cd dashboard && python3 app.py

# Sensor Simulator
cd client && python3 sensor_simulator.py
```

## Configuration

- **Broker**: Edit `broker/mosquitto.conf` for MQTT settings
- **Thresholds**: Edit `backend/alert_service.py` for alert thresholds
- **Dashboard**: Edit `dashboard/app.py` for UI customization
- **Simulator**: Edit `client/sensor_simulator.py` for sensor behavior
