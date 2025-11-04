#!/usr/bin/env python3
"""
MQTT Sensor Simulator
Simulates various IoT sensors and publishes data to MQTT broker
"""

import json
import time
import random
import paho.mqtt.client as mqtt
from datetime import datetime, timezone, timedelta
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SensorSimulator:
    def __init__(self, broker_host="127.0.0.1", broker_port=1883):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.client = mqtt.Client()
        self.client_id = "sensor_simulator_001"
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_publish = self.on_publish
        
        # Initialize start time
        self.start_time = time.time()
        
        # IST timezone (UTC+5:30)
        self.ist = timezone(timedelta(hours=5, minutes=30))
        
        # Sensor configurations
        self.sensors = {
            "temperature": {
                "sensor_id": "temp_001",
                "base_value": 22.0,
                "variance": 5.0,
                "unit": "celsius",
                "location": "room_1"
            },
            "humidity": {
                "sensor_id": "hum_001", 
                "base_value": 45.0,
                "variance": 15.0,
                "unit": "percent",
                "location": "room_1"
            },
            "pressure": {
                "sensor_id": "press_001",
                "base_value": 1013.25,
                "variance": 10.0,
                "unit": "hPa",
                "location": "room_1"
            },
            "light": {
                "sensor_id": "light_001",
                "base_value": 300.0,
                "variance": 200.0,
                "unit": "lux",
                "location": "room_1"
            }
        }
        
        self.running = False

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info("Connected to MQTT broker successfully")
            self.running = True
        else:
            logger.error(f"Failed to connect to MQTT broker. Return code: {rc}")

    def on_disconnect(self, client, userdata, rc):
        logger.info("Disconnected from MQTT broker")
        self.running = False

    def on_publish(self, client, userdata, mid):
        logger.debug(f"Message published with mid: {mid}")

    def generate_sensor_data(self, sensor_type, config):
        """Generate realistic sensor data with some randomness"""
        base_value = config["base_value"]
        variance = config["variance"]
        
        # Add some realistic variation
        value = base_value + random.uniform(-variance, variance)
        
        # Add some trending behavior (slow changes over time)
        trend = random.uniform(-0.1, 0.1)
        value += trend
        
        # Ensure values stay within reasonable bounds
        if sensor_type == "temperature":
            value = max(-10, min(50, value))  # -10°C to 50°C
        elif sensor_type == "humidity":
            value = max(0, min(100, value))   # 0% to 100%
        elif sensor_type == "pressure":
            value = max(950, min(1050, value))  # 950-1050 hPa
        elif sensor_type == "light":
            value = max(0, min(1000, value))  # 0-1000 lux
        
        return round(value, 2)

    def create_message(self, sensor_type, config, value):
        """Create JSON message for sensor data"""
        message = {
            "timestamp": self.get_ist_timestamp(),
            "client_id": self.client_id,
            "sensor_id": config["sensor_id"],
            "sensor_type": sensor_type,
            "value": value,
            "unit": config["unit"],
            "location": config["location"]
        }
        return message

    def publish_sensor_data(self, sensor_type, config):
        """Publish data for a specific sensor type"""
        value = self.generate_sensor_data(sensor_type, config)
        message = self.create_message(sensor_type, config, value)
        
        topic = f"sensors/{sensor_type}"
        payload = json.dumps(message, indent=2)
        
        try:
            result = self.client.publish(topic, payload, qos=1)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"Published {sensor_type}: {value} {config['unit']}")
            else:
                logger.error(f"Failed to publish {sensor_type} data")
        except Exception as e:
            logger.error(f"Error publishing {sensor_type} data: {e}")

    def get_ist_timestamp(self):
        """Get current timestamp in IST"""
        return datetime.now(self.ist).isoformat()


    def run(self):
        """Main simulation loop"""
        try:
            # Connect to broker
            logger.info(f"Connecting to MQTT broker at {self.broker_host}:{self.broker_port}")
            self.client.connect(self.broker_host, self.broker_port, 60)
            self.client.loop_start()
            
            # Wait for connection
            time.sleep(2)
            
            if not self.running:
                logger.error("Failed to connect to MQTT broker")
                return
            
            self.start_time = time.time()
            logger.info("Starting sensor simulation...")
            
            # Main simulation loop
            while self.running:
                try:
                    # Publish data for each sensor
                    for sensor_type, config in self.sensors.items():
                        self.publish_sensor_data(sensor_type, config)
                        time.sleep(0.5)  # Small delay between sensors
                    
                    
                    # Wait before next cycle
                    time.sleep(5)  # Publish data every 5 seconds
                    
                except KeyboardInterrupt:
                    logger.info("Simulation stopped by user")
                    break
                except Exception as e:
                    logger.error(f"Error in simulation loop: {e}")
                    time.sleep(1)
                    
        except Exception as e:
            logger.error(f"Fatal error: {e}")
        finally:
            self.client.loop_stop()
            self.client.disconnect()
            logger.info("Simulation ended")

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="MQTT Sensor Simulator")
    parser.add_argument("--host", default="localhost", help="MQTT broker host")
    parser.add_argument("--port", type=int, default=1883, help="MQTT broker port")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create and run simulator
    simulator = SensorSimulator(args.host, args.port)
    simulator.run()

if __name__ == "__main__":
    main()
