# Backend Configuration

This document describes the configuration system for the MQTT backend services.

## Configuration Files

### 1. `config.py` - Python Configuration Class
The main configuration is defined in `config.py` as a Python class with all settings and validation logic.

### 2. `config.json` - JSON Configuration File
A JSON file that can be easily modified without changing Python code. This file is used for runtime configuration.

## Data Storage Configuration

### Data Directory
- **Location**: `data/` (relative to project root)
- **Purpose**: Where all sensor data CSV files are stored
- **Backup**: Automatic backups enabled by default

### File Management
- **Retention**: Data kept for 30 days by default
- **Main File**: Keeps only last 4 hours of data (configurable)
- **File Rotation**: Automatic when files exceed 100MB
- **Backup Strategy**: Last 6 hours of data saved as backup_1, backup_2, backup_3 (rotating)
- **Backup Frequency**: Every 24 hours

### CSV Files
- **Main File**: `sensor_data.csv`
- **Headers**: timestamp, sensor_id, sensor_type, value, unit, location

### Main File Management
- **Keep Last Hours**: Configurable hours of data to keep in main file (default: 4 hours)
- **Auto Cleanup**: Automatically removes old data when file gets too large
- **Data Preservation**: Old data is preserved in backup files

### Backup System
- **Backup Files**: `backup_1.csv`, `backup_2.csv`, `backup_3.csv`
- **Content**: Last 6 hours of sensor data
- **Rotation**: When all 3 backups exist, oldest is overwritten
- **Location**: `data/backups/` directory

## MQTT Broker Configuration

### Connection Settings
- **Host**: localhost (default)
- **Port**: 1883 (default)
- **Authentication**: Optional username/password
- **QoS**: Level 1 (at least once delivery)

### Topics
The system subscribes to these sensor topics:
- `sensors/gas`
- `sensors/soil_temperature`
- `sensors/soil_moisture`
- `sensors/ph`
- `sensors/light`
- `sensors/air_temperature`
- `sensors/air_humidity`

## Data Processing Configuration

### Queue Settings
- **Max Queue Size**: 1000 messages
- **Processing Threads**: 2 threads
- **Batch Processing**: 10 messages per batch
- **Batch Timeout**: 5 seconds

### Data Validation
- **Required Fields**: timestamp, sensor_id, sensor_type, value
- **Numeric Conversion**: Automatic for numeric sensors
- **Timestamp Normalization**: Enabled

## Sensor Type Configuration

Each sensor type has specific settings:

### Gas Sensor
- **Unit**: status
- **Values**: normal_gas, toxic_gas
- **Warning Threshold**: toxic_gas

### Soil Temperature Sensor
- **Unit**: celsius
- **Range**: -10 to 50°C
- **Warning Threshold**: 35°C
- **Critical Threshold**: 40°C

### Soil Moisture Sensor
- **Unit**: %
- **Range**: 0-100%
- **Warning Threshold**: 20%
- **Critical Threshold**: 10%

### pH Sensor
- **Unit**: ph
- **Range**: 0-14
- **Warning Threshold**: 8.5
- **Critical Threshold**: 9.0

### Light Sensor
- **Unit**: lux
- **Range**: 0-100,000 lux
- **Warning Threshold**: 1,000 lux
- **Critical Threshold**: 100 lux

### Air Temperature Sensor
- **Unit**: celsius
- **Range**: -20 to 60°C
- **Warning Threshold**: 35°C
- **Critical Threshold**: 40°C

### Air Humidity Sensor
- **Unit**: %
- **Range**: 0-100%
- **Warning Threshold**: 80%
- **Critical Threshold**: 90%

## Logging Configuration

### Log Settings
- **Level**: INFO (default)
- **Directory**: `logs/`
- **File**: `backend.log`
- **Max Size**: 10MB per file
- **Backup Count**: 5 files

## Environment Variables

You can override configuration using environment variables:

- `MQTT_BROKER_HOST`: MQTT broker hostname
- `MQTT_BROKER_PORT`: MQTT broker port
- `MQTT_BROKER_USERNAME`: MQTT broker username
- `MQTT_BROKER_PASSWORD`: MQTT broker password
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)

## Usage Examples

### Check Configuration
```bash
python mqtt_subscriber.py --config-check
```

### Run with Custom Settings
```bash
python mqtt_subscriber.py --host 192.168.1.100 --port 1883 --verbose
```

### Modify Configuration
Edit `config.json` to change settings without modifying Python code:

```json
{
  "data_storage": {
    "retention_days": 60,
    "max_file_size_mb": 200
  },
  "mqtt_broker": {
    "host": "192.168.1.100",
    "port": 1883
  }
}
```

## Directory Structure

```
backend/
├── config.py          # Python configuration class
├── config.json        # JSON configuration file
├── data_storage.py    # Data storage service
├── mqtt_subscriber.py # MQTT subscriber service
└── CONFIG.md          # This documentation

data/                  # Data storage directory
├── sensor_data.csv    # Main sensor data file
└── backups/          # Backup files

logs/                  # Log files directory
└── backend.log        # Main log file
```

## Configuration Validation

The system automatically validates configuration on startup:

1. **Data Directory**: Checks if writable
2. **MQTT Settings**: Validates host and port
3. **Sensor Types**: Validates thresholds and ranges
4. **File Paths**: Ensures directories exist

## Troubleshooting

### Common Issues

1. **Permission Denied**: Ensure the data directory is writable
2. **MQTT Connection Failed**: Check broker host and port
3. **Configuration Errors**: Run with `--config-check` flag

### Debug Mode

Enable verbose logging:
```bash
python mqtt_subscriber.py --verbose
```

This will show detailed information about:
- MQTT connection status
- Message processing
- Data storage operations
- Configuration loading
