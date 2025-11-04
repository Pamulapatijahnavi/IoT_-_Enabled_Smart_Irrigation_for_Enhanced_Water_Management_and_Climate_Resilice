#!/usr/bin/env python3
"""
Backend Configuration
Configuration settings for the MQTT backend services
"""

import os
from pathlib import Path
from typing import Dict, List, Any

class Config:
    """Configuration class for backend services"""
    
    def __init__(self):
        # Base directory - project root
        self.BASE_DIR = Path(__file__).resolve().parent.parent
        
        # Data Storage Configuration
        self.DATA_STORAGE = {
            # Directory where all data will be stored
            "data_directory": self.BASE_DIR / "data",
            
            # Data retention settings
            "keep_last_hours": 6,  # Keep only last 6 hours in main file
            
            # Backup settings
            "backup_enabled": True,
            "backup_directory": self.BASE_DIR / "data" / "backups",
            
            # File size limits
            "max_file_size_mb": 100,  # Maximum CSV file size in MB
            "auto_rotate_files": True,  # Create new files when size limit reached
        }
        
        # MQTT Broker Configuration
        self.MQTT_BROKER_CONFIG_SUB = {
            "host": os.getenv("MQTT_BROKER_HOST", "localhost"),
            "port": int(os.getenv("MQTT_BROKER_PORT", "1883")),
        }
        
        # MQTT Topics Configuration
        self.MQTT_TOPICS = {
            # Sensor topics to subscribe to
            "sensor_topics": [
                "sensors/gas",
                "sensors/soil_temperature", 
                "sensors/soil_moisture",
                "sensors/ph",
                "sensors/light",
                "sensors/air_temperature",
                "sensors/air_humidity",
            ],
            
            # Topic patterns for wildcard subscriptions
            "wildcard_topics": [
                "sensors/+",  # All sensor topics
                "devices/+/sensors/+",  # Device-specific sensor topics
            ],
        }
        
        
        # Sensor Type Configuration
        self.SENSOR_TYPES = {
            "gas_sensor": {
                "threshold_warning": "toxic_gas",
            },
            "soil_temp_sensor": {
                "threshold_warning": 35,
            },
            "soil_moisture": {
                "threshold_warning": 20,
            },
            "ph_sensor": {
                "threshold_warning": 8.5,
            },
            "light_sensor": {
                "threshold_warning": 1000,
            },
            "air_temp_sensor": {
                "threshold_warning": 35,
            },
            "air_hum_sensor": {
                "threshold_warning": 80,
            },
        }
    
    def get_data_directory(self) -> Path:
        """Get the data directory path"""
        data_dir = self.DATA_STORAGE["data_directory"]
        # Convert to Path object if it's a string
        if isinstance(data_dir, str):
            data_dir = Path(data_dir)
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir
    
    def get_sensor_data_file(self) -> Path:
        """Get the sensor data CSV file path"""
        return self.get_data_directory() / "sensor_data.csv"
    
    def get_backup_directory(self) -> Path:
        """Get the backup directory path"""
        backup_dir = self.DATA_STORAGE["backup_directory"]
        # Convert to Path object if it's a string
        if isinstance(backup_dir, str):
            backup_dir = Path(backup_dir)
        backup_dir.mkdir(parents=True, exist_ok=True)
        return backup_dir
    
    
    def validate_config(self) -> List[str]:
        """Validate configuration and return any errors"""
        errors = []
        
        # Check if data directory is writable
        try:
            data_dir = self.get_data_directory()
            test_file = data_dir / "test_write.tmp"
            test_file.write_text("test")
            test_file.unlink()
        except Exception as e:
            errors.append(f"Cannot write to data directory: {e}")
        
        # Check MQTT broker settings
        if not self.MQTT_BROKER_CONFIG_SUB["host"]:
            errors.append("MQTT broker host is required")
        
        if not (1 <= self.MQTT_BROKER_CONFIG_SUB["port"] <= 65535):
            errors.append("MQTT broker port must be between 1 and 65535")
        
        # Check sensor type configurations
        for sensor_type, sensor_config in self.SENSOR_TYPES.items():
            # Check for required threshold fields based on sensor type
            if sensor_type == 'gas_sensor':
                if "threshold_warning" not in sensor_config:
                    errors.append(f"Sensor {sensor_type}: threshold_warning is required")
            elif sensor_type == 'light_sensor':
                # Light sensor has no alert conditions
                continue
            else:
                # Numeric sensors need either threshold_warning or threshold_low/threshold_high
                has_old_format = "threshold_warning" in sensor_config
                has_new_format = "threshold_low" in sensor_config or "threshold_high" in sensor_config
                if not (has_old_format or has_new_format):
                    errors.append(f"Sensor {sensor_type}: threshold configuration is required (threshold_warning or threshold_low/threshold_high)")
        
        return errors
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            "data_storage": self.DATA_STORAGE,
            "mqtt_broker_config_sub": self.MQTT_BROKER_CONFIG_SUB,
            "mqtt_topics": self.MQTT_TOPICS,
            "sensor_types": self.SENSOR_TYPES,
        }
    
    def save_to_file(self, file_path: Path = None):
        """Save configuration to a JSON file"""
        import json
        
        if file_path is None:
            file_path = self.BASE_DIR / "backend" / "config.json"
        
        with open(file_path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2, default=str)
    
    @classmethod
    def load_from_file(cls, file_path: Path = None):
        """Load configuration from a JSON file"""
        import json
        
        if file_path is None:
            file_path = Path(__file__).parent / "config.json"
        
        if file_path.exists():
            with open(file_path, 'r') as f:
                config_data = json.load(f)
            
            # Create instance and update with loaded data
            instance = cls()
            
            # Update sensor types from JSON file
            if 'sensor_types' in config_data:
                instance.SENSOR_TYPES = config_data['sensor_types']
            
            # Update other configurations if needed
            if 'data_storage' in config_data:
                instance.DATA_STORAGE.update(config_data['data_storage'])
            
            if 'mqtt_broker_config_sub' in config_data:
                instance.MQTT_BROKER_CONFIG_SUB.update(config_data['mqtt_broker_config_sub'])
            
            if 'mqtt_topics' in config_data:
                instance.MQTT_TOPICS.update(config_data['mqtt_topics'])
            
            return instance
        else:
            return cls()


# Global configuration instance - load from JSON file
config = Config.load_from_file()

# Validate configuration on import
config_errors = config.validate_config()
if config_errors:
    print("Configuration errors found:")
    for error in config_errors:
        print(f"  - {error}")
    print("Please fix these errors before running the application.")

if __name__ == "__main__":
    # Print current configuration
    print("Current Backend Configuration:")
    print("=" * 50)
    
    print(f"Data Directory: {config.get_data_directory()}")
    print(f"Sensor Data File: {config.get_sensor_data_file()}")
    print(f"Backup Directory: {config.get_backup_directory()}")
    
    print("\nMQTT Broker Settings:")
    print(f"  Host: {config.MQTT_BROKER_CONFIG_SUB['host']}")
    print(f"  Port: {config.MQTT_BROKER_CONFIG_SUB['port']}")
    
    print("\nSensor Topics:")
    for topic in config.MQTT_TOPICS['sensor_topics']:
        print(f"  - {topic}")
    
    print("\nData Retention:")
    print(f"  Keep last hours: {config.DATA_STORAGE['keep_last_hours']}")
    print(f"  Max file size: {config.DATA_STORAGE['max_file_size_mb']} MB")
    print(f"  Auto rotate files: {config.DATA_STORAGE['auto_rotate_files']}")
    
    # Save configuration to file
    config.save_to_file()
    print(f"\nConfiguration saved to: {config.BASE_DIR / 'backend' / 'config.json'}")
