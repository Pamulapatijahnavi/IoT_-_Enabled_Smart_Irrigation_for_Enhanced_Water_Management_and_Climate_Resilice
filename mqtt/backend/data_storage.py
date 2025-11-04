#!/usr/bin/env python3
"""
Data Storage Service
Handles CSV file storage for sensor data
"""

import csv
import os
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from config import config

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DataStorage:
    def __init__(self, data_dir=None):
        # Use configuration if no data_dir provided
        if data_dir is None:
            self.data_dir = config.get_data_directory()
        else:
            self.data_dir = Path(data_dir)
            self.data_dir.mkdir(exist_ok=True)
        
        # CSV file paths - hardcoded
        self.sensor_data_file = self.data_dir / "sensor_data.csv"
        
        # Initialize CSV files with headers
        self.initialize_csv_files()
        
        logger.info(f"Data storage initialized. Data directory: {self.data_dir.absolute()}")

    def initialize_csv_files(self):
        """Initialize CSV files with proper headers"""
        # Sensor data CSV headers - simplified to match requirements
        sensor_headers = [
            "timestamp", "sensor_id", "sensor_type", 
            "value", "unit", "location"
        ]
        
        
        # Create sensor data file if it doesn't exist
        if not self.sensor_data_file.exists():
            with open(self.sensor_data_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(sensor_headers)
            logger.info(f"Created sensor data file: {self.sensor_data_file}")
        

    def store_sensor_data(self, message):
        """Store sensor data to CSV file"""
        try:
            # Extract data from message - simplified to match requirements
            row_data = [
                message.get("timestamp", ""),
                message.get("sensor_id", ""),
                message.get("sensor_type", ""),
                message.get("value", ""),
                message.get("unit", ""),
                message.get("location", "")
            ]
            
            # Append to CSV file
            with open(self.sensor_data_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(row_data)
            
            logger.info(f"Successfully stored sensor data: {message.get('sensor_type')} = {message.get('value')} to {self.sensor_data_file}")
            
        except Exception as e:
            logger.error(f"Error storing sensor data: {e}")
            logger.error(f"Message data: {message}")
            logger.error(f"Target file: {self.sensor_data_file}")
            raise


    def get_recent_sensor_data(self, sensor_type=None, limit=100):
        """Get recent sensor data from CSV file"""
        try:
            data = []
            with open(self.sensor_data_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                
                # Filter by sensor type if specified
                if sensor_type:
                    rows = [row for row in rows if row.get('sensor_type') == sensor_type]
                
                # Get most recent data
                data = rows[-limit:] if limit else rows
                
            return data
            
        except Exception as e:
            logger.error(f"Error reading sensor data: {e}")
            return []

    def get_sensor_data_by_timeframe(self, start_time, end_time, sensor_type=None):
        """Get sensor data within a specific timeframe"""
        try:
            data = []
            with open(self.sensor_data_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    timestamp = row.get('timestamp', '')
                    if start_time <= timestamp <= end_time:
                        if not sensor_type or row.get('sensor_type') == sensor_type:
                            data.append(row)
            
            return data
            
        except Exception as e:
            logger.error(f"Error reading sensor data by timeframe: {e}")
            return []

    def get_statistics(self):
        """Get basic statistics about stored data"""
        try:
            stats = {
                "sensor_data_count": 0,
                "sensor_types": set(),
                "locations": set(),
                "date_range": {"earliest": None, "latest": None}
            }
            
            # Count sensor data
            with open(self.sensor_data_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    stats["sensor_data_count"] += 1
                    stats["sensor_types"].add(row.get('sensor_type', ''))
                    stats["locations"].add(row.get('location', ''))
                    
                    timestamp = row.get('timestamp', '')
                    if timestamp:
                        if not stats["date_range"]["earliest"] or timestamp < stats["date_range"]["earliest"]:
                            stats["date_range"]["earliest"] = timestamp
                        if not stats["date_range"]["latest"] or timestamp > stats["date_range"]["latest"]:
                            stats["date_range"]["latest"] = timestamp
            
            
            # Convert sets to lists for JSON serialization
            stats["sensor_types"] = list(stats["sensor_types"])
            stats["locations"] = list(stats["locations"])
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {}

    def cleanup_old_data(self, hours_to_keep=None):
        """Remove data older than specified hours"""
        if hours_to_keep is None:
            hours_to_keep = config.DATA_STORAGE["keep_last_hours"]
        
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours_to_keep)
            cutoff_iso = cutoff_time.isoformat() + "Z"
            
            # Clean sensor data
            temp_file = self.sensor_data_file.with_suffix('.tmp')
            with open(self.sensor_data_file, 'r', encoding='utf-8') as infile, \
                 open(temp_file, 'w', newline='', encoding='utf-8') as outfile:
                
                reader = csv.DictReader(infile)
                writer = csv.DictWriter(outfile, fieldnames=reader.fieldnames)
                writer.writeheader()
                
                for row in reader:
                    if row.get('timestamp', '') >= cutoff_iso:
                        writer.writerow(row)
            
            temp_file.replace(self.sensor_data_file)
            logger.info(f"Cleaned up sensor data older than {hours_to_keep} hours")
            
        except Exception as e:
            logger.error(f"Error cleaning up old data: {e}")

    def create_backup(self, data_to_backup):
        """Create a backup of the provided data"""
        if not config.DATA_STORAGE["backup_enabled"]:
            return None
        
        try:
            backup_dir = config.get_backup_directory()
            
            # Get the next backup number (1 or 2)
            backup_number = self._get_next_backup_number()
            backup_file = backup_dir / f"backup_{backup_number}.csv"
            
            logger.info(f"Creating backup: {backup_file}")
            
            # Write data to backup file
            if data_to_backup:
                with open(backup_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=data_to_backup[0].keys())
                    writer.writeheader()
                    writer.writerows(data_to_backup)
                
                logger.info(f"Backup created: {backup_file} with {len(data_to_backup)} records")
                return backup_file
            else:
                logger.info("No data to backup")
                return None
            
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            return None

    def _get_next_backup_number(self):
        """Get the next backup number (1 or 2) in rotation"""
        backup_dir = config.get_backup_directory()
        
        # Check which backup files exist
        existing_backups = []
        for i in range(1, 3):  # Check backup_1, backup_2
            backup_file = backup_dir / f"backup_{i}.csv"
            if backup_file.exists():
                existing_backups.append(i)
        
        # If no backups exist, start with 1
        if not existing_backups:
            return 1
        
        # If both backups exist, use the oldest one (rotate)
        if len(existing_backups) == 2:
            # Find the oldest backup by modification time
            oldest_backup = 1
            oldest_time = float('inf')
            
            for i in range(1, 3):
                backup_file = backup_dir / f"backup_{i}.csv"
                if backup_file.exists():
                    mod_time = backup_file.stat().st_mtime
                    if mod_time < oldest_time:
                        oldest_time = mod_time
                        oldest_backup = i
            
            return oldest_backup
        
        # Otherwise, use the next available number
        for i in range(1, 3):
            if i not in existing_backups:
                return i
        
        return 1  # Fallback

    def get_file_size_mb(self):
        """Get the size of the sensor data file in MB"""
        try:
            if self.sensor_data_file.exists():
                return self.sensor_data_file.stat().st_size / (1024 * 1024)
            return 0
        except Exception as e:
            logger.error(f"Error getting file size: {e}")
            return 0

    def should_rotate_file(self):
        """Check if the file should be rotated based on size"""
        if not config.DATA_STORAGE["auto_rotate_files"]:
            return False
        
        max_size_mb = config.DATA_STORAGE["max_file_size_mb"]
        current_size_mb = self.get_file_size_mb()
        
        return current_size_mb >= max_size_mb

    def rotate_file(self):
        """Rotate the sensor data file when it gets too large"""
        try:
            if not self.should_rotate_file():
                return
            
            # Create backup before rotation
            self.create_backup()
            
            # Create new file with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            old_file = self.sensor_data_file.with_suffix(f".{timestamp}.csv")
            
            # Move current file to archived name
            self.sensor_data_file.rename(old_file)
            
            # Create new empty file with headers
            self.initialize_csv_files()
            
            logger.info(f"File rotated: {old_file}")
            
        except Exception as e:
            logger.error(f"Error rotating file: {e}")

    def get_backup_info(self):
        """Get information about existing backups"""
        backup_dir = config.get_backup_directory()
        backup_info = {}
        
        for i in range(1, 4):
            backup_file = backup_dir / f"backup_{i}.csv"
            if backup_file.exists():
                stat = backup_file.stat()
                backup_info[f"backup_{i}"] = {
                    "file": str(backup_file),
                    "size_mb": round(stat.st_size / (1024 * 1024), 2),
                    "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                }
            else:
                backup_info[f"backup_{i}"] = None
        
        return backup_info

    def cleanup_old_backups(self):
        """Remove old backup files (keep only backup_1, backup_2, backup_3)"""
        backup_dir = config.get_backup_directory()
        
        try:
            # Remove any backup files that don't match the naming pattern
            for file in backup_dir.glob("*.csv"):
                if not file.name.startswith("backup_") or not file.name.endswith(".csv"):
                    continue
                
                # Check if it's one of our numbered backups
                if file.name not in ["backup_1.csv", "backup_2.csv", "backup_3.csv"]:
                    file.unlink()
                    logger.info(f"Removed old backup file: {file}")
            
        except Exception as e:
            logger.error(f"Error cleaning up old backups: {e}")

    def cleanup_main_file(self):
        """Keep only the last N hours of data in the main sensor data file, backup older data first"""
        try:
            keep_hours = config.DATA_STORAGE["keep_last_hours"]
            cutoff_time = datetime.now() - timedelta(hours=keep_hours)
            
            logger.info(f"Cleaning up main file to keep only last {keep_hours} hours")
            logger.debug(f"Cutoff time: {cutoff_time.isoformat()}")
            
            # Read all data and separate recent vs old data
            recent_data = []
            old_data = []
            fieldnames = None
            
            with open(self.sensor_data_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                fieldnames = reader.fieldnames
                
                for row in reader:
                    timestamp = row.get('timestamp', '')
                    if timestamp:
                        try:
                            # Parse timestamp and convert to naive datetime for comparison
                            if 'Z' in timestamp:
                                # UTC format: 2025-10-05T10:00:31.099929Z
                                ts_obj = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                                ts_obj = ts_obj.replace(tzinfo=None)
                            elif '+' in timestamp:
                                # Timezone format: 2025-10-05T13:00:31.094664+05:30
                                ts_obj = datetime.fromisoformat(timestamp)
                                ts_obj = ts_obj.replace(tzinfo=None)
                            elif timestamp.count('-') > 2:
                                # ISO format without timezone: 2025-10-05T13:00:31.094664
                                ts_obj = datetime.fromisoformat(timestamp)
                            else:
                                # Skip unknown formats
                                continue
                            
                            logger.debug(f"Comparing: {ts_obj} >= {cutoff_time} = {ts_obj >= cutoff_time}")
                            if ts_obj >= cutoff_time:
                                recent_data.append(row)
                                logger.debug(f"Keeping recent data: {timestamp}")
                            else:
                                old_data.append(row)
                                logger.debug(f"Archiving old data: {timestamp}")
                        except Exception as e:
                            logger.debug(f"Error parsing timestamp {timestamp}: {e}")
                            continue
            
            logger.info(f"Found {len(recent_data)} recent records and {len(old_data)} old records")
            
            # Backup old data before removing it
            if old_data:
                backup_file = self.create_backup(old_data)
                if backup_file:
                    logger.info(f"Successfully backed up {len(old_data)} old records to {backup_file}")
                else:
                    logger.error("Failed to create backup - aborting cleanup to prevent data loss")
                    return
            
            # Write only recent data back to main file
            if recent_data:
                temp_file = self.sensor_data_file.with_suffix('.tmp')
                with open(temp_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(recent_data)
                
                # Replace original file
                temp_file.replace(self.sensor_data_file)
                logger.info(f"Main file cleaned up. Kept {len(recent_data)} records from last {keep_hours} hours")
            else:
                logger.info("No recent data found to keep")
                
        except Exception as e:
            logger.error(f"Error cleaning up main file: {e}")

    def auto_cleanup_main_file(self):
        """Automatically clean up main file if it gets too large"""
        try:
            # Check if file size exceeds limit
            if self.should_rotate_file():
                logger.info("Main file size limit reached, cleaning up to keep only recent data")
                self.cleanup_main_file()
                
        except Exception as e:
            logger.error(f"Error in auto cleanup: {e}")

if __name__ == "__main__":
    # Test the data storage service
    storage = DataStorage()
    
    # Test sensor data storage with current timestamp
    current_time = datetime.now()
    test_message = {
        "timestamp": current_time.isoformat() + "Z",
        "received_at": current_time.isoformat() + "Z",
        "sensor_id": "test_001",
        "sensor_type": "temperature",
        "value": 25.5,
        "unit": "celsius",
        "location": "test_room",
        "topic": "sensors/temperature"
    }
    
    storage.store_sensor_data(test_message)
    print("Test data stored successfully")
    
    # Test backup functionality
    print("\nTesting backup functionality...")
    backup_file = storage.create_backup()
    if backup_file:
        print(f"Backup created: {backup_file}")
    else:
        print("No backup created (no data from last 6 hours)")
    
    # Show backup info
    backup_info = storage.get_backup_info()
    print(f"\nBackup information: {backup_info}")
    
    # Test cleanup functionality
    print(f"\nTesting main file cleanup...")
    print(f"Current file size: {storage.get_file_size_mb():.2f} MB")
    
    # Clean up main file to keep only last 4 hours
    storage.cleanup_main_file()
    
    print(f"After cleanup file size: {storage.get_file_size_mb():.2f} MB")
    
    # Get statistics
    stats = storage.get_statistics()
    print(f"\nStatistics: {stats}")
