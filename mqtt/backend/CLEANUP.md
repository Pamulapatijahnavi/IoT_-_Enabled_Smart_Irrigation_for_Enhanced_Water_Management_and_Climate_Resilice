# Automatic Data Cleanup and Backup System

## Overview

The MQTT system now includes an automatic cleanup and backup mechanism that ensures the main `sensor_data.csv` file doesn't grow indefinitely while preserving historical data in backup files.

## How It Works

### 1. Automatic Backup
- **Frequency**: Every 6 hours (configurable)
- **Content**: Last 6 hours of sensor data
- **Files**: `backup_1.csv`, `backup_2.csv`, `backup_3.csv` (rotating)
- **Location**: `data/backups/` directory

### 2. Automatic Cleanup
- **Frequency**: Every 1 hour (configurable)
- **Action**: Removes data older than 4 hours from main file
- **Result**: Main file keeps only recent data

### 3. Data Flow
```
New Data → sensor_data.csv (grows)
    ↓
Every 6 hours: Backup last 6 hours → backup_X.csv
    ↓
Every 1 hour: Remove old data from sensor_data.csv
    ↓
Result: sensor_data.csv contains only last 4 hours
```

## Configuration

### config.json
```json
{
  "data_storage": {
    "keep_last_hours": 4,           // Keep only last 4 hours in main file
    "backup_frequency_hours": 6,    // Backup every 6 hours
    "cleanup_frequency_hours": 1,   // Cleanup every 1 hour
    "backup_enabled": true
  }
}
```

### Key Settings
- **keep_last_hours**: How much data to keep in main file (default: 4 hours)
- **backup_frequency_hours**: How often to create backups (default: 6 hours)
- **cleanup_frequency_hours**: How often to clean main file (default: 1 hour)

## File Management

### Main File (`sensor_data.csv`)
- Contains only the last 4 hours of data
- Automatically cleaned every hour
- Used by dashboard for real-time monitoring

### Backup Files (`backup_1.csv`, `backup_2.csv`, `backup_3.csv`)
- Contains last 6 hours of data when backup was created
- Rotating system (oldest backup is overwritten)
- Preserves historical data for analysis

## Monitoring

The MQTT subscriber now logs cleanup and backup activities:

```
INFO - Running scheduled backup...
INFO - Backup completed: /path/to/backup_1.csv
INFO - Running scheduled cleanup...
INFO - Cleanup completed - old data removed from main file
```

## Testing

Run the test script to verify the cleanup mechanism:

```bash
cd backend
python test_cleanup.py
```

This will:
1. Show current file size and record count
2. Create a backup
3. Run cleanup
4. Show the reduction in file size and records
5. Display backup file information

## Benefits

1. **Prevents File Bloat**: Main file stays manageable
2. **Preserves History**: Important data saved in backups
3. **Automatic**: No manual intervention required
4. **Configurable**: Adjust intervals as needed
5. **Safe**: Data is backed up before cleanup

## Troubleshooting

### If cleanup isn't working:
1. Check MQTT subscriber logs for cleanup messages
2. Verify configuration values in `config.json`
3. Run `python test_cleanup.py` to test manually

### If backups aren't created:
1. Ensure `backup_enabled: true` in config
2. Check backup directory permissions
3. Verify there's data older than 6 hours to backup

### File size still growing:
1. Check if cleanup is running (look for cleanup logs)
2. Verify `keep_last_hours` setting
3. Ensure MQTT subscriber is running continuously
