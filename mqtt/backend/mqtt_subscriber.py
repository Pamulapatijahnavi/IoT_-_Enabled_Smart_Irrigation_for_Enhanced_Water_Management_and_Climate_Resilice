#!/usr/bin/env python3
"""
MQTT Subscriber Service
Subscribes to MQTT topics and processes sensor data
"""

import json
import paho.mqtt.client as mqtt
import logging
from datetime import datetime, timezone, timedelta
import threading
import queue
import time
from data_storage import DataStorage
from config import config



# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MQTTSubscriber:
    def __init__(self, broker_host=None, broker_port=None):
        # Use configuration values if not provided
        self.broker_host = broker_host or config.MQTT_BROKER_CONFIG_SUB["host"]
        self.broker_port = broker_port or config.MQTT_BROKER_CONFIG_SUB["port"]
        
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message
        
        # Data processing queue with default size
        self.data_queue = queue.Queue(maxsize=1000)
        
        # Initialize services using configuration
        self.data_storage = DataStorage()
        
        # IST timezone (UTC+5:30)
        self.ist = timezone(timedelta(hours=5, minutes=30))
        
        # Statistics
        self.stats = {
            "messages_received": 0,
            "messages_processed": 0,
            "errors": 0,
            "start_time": None
        }
        
        # Client tracking
        self.connected_clients = {}
        self.client_stats = {}
        
        # Cleanup scheduling - now size-based instead of time-based
        self.last_cleanup_time = None
        self.last_backup_time = None
        
        self.running = True

    def get_ist_timestamp(self):
        """Get current timestamp in IST"""
        return datetime.now(self.ist).isoformat()

    def track_client_connection(self, client_id, action="connect"):
        """Track client connections and disconnections"""
        current_time = self.get_ist_timestamp()
        
        if action == "connect":
            self.connected_clients[client_id] = {
                "connected_at": current_time,
                "last_seen": current_time,
                "message_count": 0
            }
            logger.info(f"Client connected: {client_id} at {current_time}")
        elif action == "disconnect":
            if client_id in self.connected_clients:
                connection_duration = self.connected_clients[client_id]
                del self.connected_clients[client_id]
                logger.info(f"Client disconnected: {client_id} at {current_time}")
        elif action == "message":
            if client_id in self.connected_clients:
                self.connected_clients[client_id]["last_seen"] = current_time
                self.connected_clients[client_id]["message_count"] += 1

    def get_client_info(self, client_id):
        """Get information about a specific client"""
        if client_id in self.connected_clients:
            return self.connected_clients[client_id]
        return None

    def get_all_clients(self):
        """Get information about all connected clients"""
        return self.connected_clients.copy()

    def extract_client_id(self, msg):
        """Extract client ID from message - this is a simplified approach"""
        # In a real implementation, you might need to use MQTT broker APIs
        # For now, we'll use a pattern-based approach or message content
        try:
            # Try to extract from message payload if it contains client info
            message_data = json.loads(msg.payload.decode())
            if 'device_id' in message_data:
                return message_data['device_id']
            elif 'client_id' in message_data:
                return message_data['client_id']
        except:
            pass
        
        # Fallback: use a hash of the message or topic pattern
        # This is not ideal but works for demonstration
        return f"client_{hash(msg.topic) % 1000}"

    def on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            logger.info(f"Connected to MQTT broker successfully at {self.broker_host}:{self.broker_port}")
            
            # Subscribe to topics from configuration
            topics = config.MQTT_TOPICS["sensor_topics"]
            qos_level = 1  # Default QoS level
            
            for topic in topics:
                result = client.subscribe(topic, qos=qos_level)
                if result[0] == mqtt.MQTT_ERR_SUCCESS:
                    logger.info(f"Subscribed to topic: {topic} (QoS: {qos_level})")
                else:
                    logger.error(f"Failed to subscribe to topic: {topic}")
            
            # Also subscribe to wildcard topics if configured
            wildcard_topics = config.MQTT_TOPICS.get("wildcard_topics", [])
            for topic in wildcard_topics:
                result = client.subscribe(topic, qos=qos_level)
                if result[0] == mqtt.MQTT_ERR_SUCCESS:
                    logger.info(f"Subscribed to wildcard topic: {topic} (QoS: {qos_level})")
                else:
                    logger.error(f"Failed to subscribe to wildcard topic: {topic}")
            
            self.stats["start_time"] = time.time()
        else:
            logger.error(f"Failed to connect to MQTT broker. Reason code: {reason_code}")

    def on_disconnect(self, client, userdata, reason_code, properties):
        logger.info("Disconnected from MQTT broker")
        self.running = False

    def on_message(self, client, userdata, msg):
        """Handle incoming MQTT messages"""
        try:
            self.stats["messages_received"] += 1
            
            # Extract client information from message
            client_id = self.extract_client_id(msg)
            if client_id:
                self.track_client_connection(client_id, "message")
            
            # Parse JSON message
            message = json.loads(msg.payload.decode())
            message["topic"] = msg.topic
            message["received_at"] = self.get_ist_timestamp()
            message["client_id"] = client_id  # Add client ID to message
            
            # Ensure timestamp field exists (use received_at if timestamp not provided)
            if "timestamp" not in message:
                message["timestamp"] = message["received_at"]
            
            # Log the received message details
            sensor_id = message.get('sensor_id', 'unknown')
            sensor_type = message.get('sensor_type', 'unknown')
            value = message.get('value', 'unknown')
            unit = message.get('unit', 'unknown')
            location = message.get('location', 'unknown')
            
            logger.info(f"Received {sensor_type} from {sensor_id} at {location}: {value} {unit}")
            
            # Add to processing queue
            self.data_queue.put(message)
            logger.debug(f"Added message to queue. Queue size: {self.data_queue.qsize()}")
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON message: {e}")
            self.stats["errors"] += 1
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            self.stats["errors"] += 1

    def process_message(self, message):
        """Process individual message"""
        try:
            topic = message.get("topic", "")
            sensor_type = message.get("sensor_type", "")
            client_id = message.get("client_id", "unknown")
            
            # Track client activity
            if client_id != "unknown":
                self.track_client_connection(client_id, "message")
            
            if topic.startswith("sensors/"):
                # Process sensor data
                self.process_sensor_data(message)
            else:
                logger.warning(f"Unknown topic: {topic}")
            
            self.stats["messages_processed"] += 1
            logger.debug(f"Processed {sensor_type} message from {message.get('sensor_id', 'unknown')} (client: {client_id})")
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            self.stats["errors"] += 1

    def process_sensor_data(self, message):
        """Process sensor data message"""
        try:
            sensor_id = message.get('sensor_id', 'unknown')
            sensor_type = message.get('sensor_type', 'unknown')
            value = message.get('value', '')
            unit = message.get('unit', '')
            location = message.get('location', 'unknown')
            
            logger.info(f"Processing {sensor_type} message from {sensor_id}")
            
            # Convert string values to appropriate numeric types for threshold checking
            processed_message = self._convert_sensor_value(message)
            
            logger.info(f"About to store data to CSV: {processed_message}")
            
            # Store data to CSV
            self.data_storage.store_sensor_data(processed_message)
            
            logger.info(f"Successfully stored {sensor_type} data from {sensor_id} at {location}: {processed_message.get('value')} {unit}")
            
        except Exception as e:
            logger.error(f"Error processing sensor data: {e}")
            logger.error(f"Message that failed: {message}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            self.stats["errors"] += 1


    def _convert_sensor_value(self, message):
        """Convert string sensor values to appropriate numeric types"""
        try:
            # Create a copy of the message
            processed_message = message.copy()
            sensor_type = message.get('sensor_type', '')
            value = message.get('value', '')
            
            # Convert value based on sensor type
            if sensor_type == 'gas_sensor':
                # Gas sensor sends "normal_gas" or "toxic_gas" - keep as string
                processed_message['value'] = str(value)
                logger.debug(f"Gas sensor value kept as string: {processed_message['value']}")
            elif sensor_type in ['soil_temp_sensor', 'air_temp_sensor', 'moisture_sensor', 'air_hum_sensor', 'ph_sensor']:
                try:
                    # Convert string to float for numeric sensors
                    processed_message['value'] = float(value)
                    logger.debug(f"Converted {sensor_type} value '{value}' to float: {processed_message['value']}")
                except (ValueError, TypeError):
                    logger.warning(f"Could not convert {sensor_type} value '{value}' to float, keeping as string")
                    processed_message['value'] = value  # Keep original value
            elif sensor_type == 'light_sensor':
                # Light sensor sends "light" or "dark" - keep as string
                processed_message['value'] = str(value)
                logger.debug(f"Light sensor value kept as string: {processed_message['value']}")
            else:
                # Keep original value for unknown sensor types
                processed_message['value'] = value
                logger.debug(f"Unknown sensor type '{sensor_type}', keeping value as: {processed_message['value']}")
                
            return processed_message
            
        except Exception as e:
            logger.error(f"Error converting sensor value: {e}")
            return message

    def _is_numeric_sensor(self, sensor_type):
        """Check if sensor type should have numeric threshold checking"""
        numeric_sensors = ['soil_temp_sensor', 'air_temp_sensor', 'moisture_sensor', 'air_hum_sensor', 'ph_sensor']
        return sensor_type in numeric_sensors

    def data_processor(self):
        """Background thread for processing queued messages"""
        logger.info("Data processor thread started")
        batch_size = 10  # Default batch size
        batch_timeout = 5  # Default batch timeout in seconds
        
        while self.running:
            try:
                # Process messages in batches if configured
                if batch_size > 1:
                    self._process_batch(batch_size, batch_timeout)
                else:
                    # Process single message
                    message = self.data_queue.get(timeout=1.0)
                    sensor_type = message.get('sensor_type', 'unknown')
                    sensor_id = message.get('sensor_id', 'unknown')
                    logger.info(f"Processing {sensor_type} message from {sensor_id}")
                    self.process_message(message)
                    self.data_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error in data processor: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                time.sleep(1)

    def _process_batch(self, batch_size, timeout_seconds):
        """Process messages in batches"""
        batch = []
        start_time = time.time()
        
        # Collect messages for batch processing
        while len(batch) < batch_size and (time.time() - start_time) < timeout_seconds:
            try:
                message = self.data_queue.get(timeout=0.1)
                batch.append(message)
            except queue.Empty:
                break
        
        if batch:
            logger.info(f"Processing batch of {len(batch)} messages")
            for message in batch:
                try:
                    self.process_message(message)
                    self.data_queue.task_done()
                except Exception as e:
                    logger.error(f"Error processing message in batch: {e}")
                    self.data_queue.task_done()

    def should_run_cleanup(self):
        """Check if cleanup should be run based on file size"""
        # Check if file size exceeds limit
        if self.data_storage.should_rotate_file():
            return True
        
        # Also run cleanup if we haven't done it in the last hour (safety check)
        if self.last_cleanup_time is None:
            return True
        
        time_since_cleanup = datetime.now() - self.last_cleanup_time
        return time_since_cleanup.total_seconds() >= 3600  # 1 hour

    def run_cleanup_if_needed(self):
        """Run cleanup operations if file size exceeds limit"""
        try:
            current_time = datetime.now()
            
            # Run cleanup if file is too large
            if self.should_run_cleanup():
                logger.info("File size limit reached - running cleanup...")
                self.data_storage.cleanup_main_file()
                logger.info("Cleanup completed - old data backed up and removed from main file")
                self.last_cleanup_time = current_time
                
        except Exception as e:
            logger.error(f"Error in cleanup: {e}")

    def run_backup_and_cleanup(self):
        """Run backup and cleanup operations"""
        try:
            current_time = datetime.now()
            
            # Run cleanup if needed
            self.run_cleanup_if_needed()
            
            # Update backup time if cleanup was performed
            if self.last_cleanup_time and self.last_cleanup_time == current_time:
                self.last_backup_time = current_time
                
        except Exception as e:
            logger.error(f"Error in backup and cleanup: {e}")

    def print_stats(self):
        """Print processing statistics"""
        if self.stats["start_time"]:
            uptime = time.time() - self.stats["start_time"]
            logger.info(f"Stats - Uptime: {uptime:.1f}s, "
                       f"Received: {self.stats['messages_received']}, "
                       f"Processed: {self.stats['messages_processed']}, "
                       f"Errors: {self.stats['errors']}, "
                       f"Connected Clients: {len(self.connected_clients)}")
            
            # Print client details
            if self.connected_clients:
                logger.info("Connected Clients:")
                for client_id, info in self.connected_clients.items():
                    logger.info(f"  - {client_id}: {info['message_count']} messages, last seen: {info['last_seen']}")
            
            # Print cleanup status
            if self.last_backup_time:
                logger.info(f"Last backup: {self.last_backup_time.strftime('%Y-%m-%d %H:%M:%S')}")
            if self.last_cleanup_time:
                logger.info(f"Last cleanup: {self.last_cleanup_time.strftime('%Y-%m-%d %H:%M:%S')}")

    def run(self):
        """Main subscriber loop"""
        try:
            # Connect to broker
            logger.info(f"Connecting to MQTT broker at {self.broker_host}:{self.broker_port}")
            self.client.connect(self.broker_host, self.broker_port, 60)
            
            # Start data processing thread
            processor_thread = threading.Thread(target=self.data_processor, daemon=True)
            processor_thread.start()
            
            # Start MQTT loop
            self.client.loop_start()
            
            # Wait for connection
            time.sleep(2)
            
            if not self.running:
                logger.error("Failed to connect to MQTT broker")
                return
            
            logger.info("MQTT subscriber started successfully")
            
            # Main loop
            try:
                while self.running:
                    time.sleep(10)  # Print stats every 10 seconds
                    self.print_stats()
                    
                    # Run backup and cleanup operations
                    self.run_backup_and_cleanup()
                    
            except KeyboardInterrupt:
                logger.info("Subscriber stopped by user")
                
        except Exception as e:
            logger.error(f"Fatal error: {e}")
        finally:
            self.client.loop_stop()
            self.client.disconnect()
            logger.info("MQTT subscriber ended")

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="MQTT Subscriber Service")
    parser.add_argument("--host", default=None, help="MQTT broker host (overrides config)")
    parser.add_argument("--port", type=int, default=None, help="MQTT broker port (overrides config)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    parser.add_argument("--config-check", action="store_true", help="Check configuration and exit")
    
    args = parser.parse_args()
    
    if args.config_check:
        # Validate configuration
        errors = config.validate_config()
        if errors:
            print("Configuration errors found:")
            for error in errors:
                print(f"  - {error}")
            return 1
        else:
            print("Configuration is valid")
            return 0
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create and run subscriber
    subscriber = MQTTSubscriber(args.host, args.port)
    subscriber.run()

if __name__ == "__main__":
    main()
