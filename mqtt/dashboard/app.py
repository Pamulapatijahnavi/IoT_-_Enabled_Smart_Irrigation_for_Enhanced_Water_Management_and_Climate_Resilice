#!/usr/bin/env python3
"""
Real-time IoT Dashboard
Plotly Dash application for visualizing sensor data
"""

import dash
from dash import dcc, html, Input, Output, State, callback
import plotly.graph_objs as go
import plotly.express as px
import pandas as pd
import json
import os
import time
from datetime import datetime, timedelta
import queue
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

data_points = 20
last_records = data_points * 7

# Initialize Dash app
app = dash.Dash(__name__)
app.title = "IoT Sensor Dashboard"

# Data storage - use dynamic paths
BASE_DIR = Path(__file__).resolve().parent.parent  # Go up one level from dashboard/ to project root
data_storage_path = BASE_DIR / "data" / "sensor_data.csv"
config_path = BASE_DIR / "backend" / "config.json"

# Global data cache
data_cache = {
    "sensor_data": pd.DataFrame(),
    "last_update": None,
    "sensor_config": {}
}

# Data update queue
data_queue = queue.Queue()


def load_sensor_config():
    """Load sensor configuration from config.json"""
    global data_cache
    
    try:
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = json.load(f)
                data_cache["sensor_config"] = config.get("sensor_types", {})
                logger.info("Sensor configuration loaded successfully")
        else:
            logger.warning(f"Config file not found: {config_path}")
            data_cache["sensor_config"] = {}
    except Exception as e:
        logger.error(f"Error loading sensor config: {e}")
        data_cache["sensor_config"] = {}

def get_sensor_thresholds(sensor_type):
    """Get threshold values for a sensor type"""
    config = data_cache.get("sensor_config", {})
    
    # Map dashboard sensor types to config sensor types
    sensor_mapping = {
        'atmosphere_temperature': 'air_temp_sensor',
        'atmosphere_humidity': 'air_hum_sensor',
        'soil_temperature': 'soil_temp_sensor',
        'soil_moisture': 'moisture_sensor',
        'toxic_gas': 'gas_sensor',
        'ph': 'ph_sensor',
        'light': 'light_sensor'
    }
    
    config_sensor_type = sensor_mapping.get(sensor_type)
    if not config_sensor_type or config_sensor_type not in config:
        return None
    
    sensor_config = config[config_sensor_type]
    
    # Handle special cases
    if sensor_type == 'toxic_gas':
        return {
            'threshold_warning': sensor_config.get('threshold_warning', 'toxic_gas'),
            'ideal_range': sensor_config.get('ideal_range', 'normal_gas')
        }
    elif sensor_type == 'light':
        return None  # No thresholds for light sensor
    
    # For numeric sensors, return threshold values
    return {
        'threshold_low': sensor_config.get('threshold_low'),
        'threshold_high': sensor_config.get('threshold_high'),
        'ideal_range': sensor_config.get('ideal_range', '')
    }

def load_data():
    """Load data from CSV files - optimized to load only recent data with sliding window"""
    global data_cache
    
    try:
        # Load sensor data - only last 30 rows for performance
        if data_storage_path.exists():
            logger.info(f"Loading sensor data from: {data_storage_path}")
            
            # Count total lines first to calculate skiprows
            with open(data_storage_path, 'r') as f:
                total_lines = sum(1 for _ in f)
            
            # Load only last rows for sliding window
            skip_rows = max(0, total_lines - last_records)
            logger.info(f"Loading last {last_records} rows (skipping first {skip_rows} rows) for sliding window")
            
            df_sensors = pd.read_csv(data_storage_path, header=None, names=[
                'timestamp', 'device_id', 'sensor_type', 'value', 'unit', 'location'
            ], skiprows=skip_rows)
            
            logger.info(f"Loaded sensor data shape: {df_sensors.shape}")
            
            if not df_sensors.empty:
                # Parse timestamps properly
                df_sensors['timestamp'] = pd.to_datetime(df_sensors['timestamp'], errors='coerce', utc=True)
                #df_sensors['timestamp'] = pd.to_datetime(df_sensors['timestamp'], errors='coerce')
                
                # Remove timezone info for easier handling
                if df_sensors['timestamp'].dt.tz is not None:
                    df_sensors['timestamp'] = df_sensors['timestamp'].dt.tz_localize(None)
                
                df_sensors = df_sensors.sort_values('timestamp')
                
                # Map sensor types to dashboard categories
                sensor_type_mapping = {
                    'gas_sensor': 'toxic_gas',
                    'soil_temp_sensor': 'soil_temperature',
                    'air_temp_sensor': 'atmosphere_temperature', 
                    'moisture_sensor': 'soil_moisture',
                    'air_hum_sensor': 'atmosphere_humidity',
                    'ph_sensor': 'ph',
                    'light_sensor': 'light'
                }
                
                # Handle text values for light sensor before converting to numeric
                light_mask = df_sensors['sensor_type'] == 'light_sensor'
                
                # Convert text light values to numeric before general conversion
                for idx, row in df_sensors[light_mask].iterrows():
                    original_value = df_sensors.loc[idx, 'value']
                    if isinstance(original_value, str):
                        if original_value.lower() == 'light':
                            df_sensors.loc[idx, 'value'] = 1
                        elif original_value.lower() == 'dark':
                            df_sensors.loc[idx, 'value'] = 0
                        else:
                            df_sensors.loc[idx, 'value'] = 0
                
                # Handle text values for gas sensor before converting to numeric
                gas_mask = df_sensors['sensor_type'] == 'gas_sensor'
                
                # Convert text gas values to numeric before general conversion
                for idx, row in df_sensors[gas_mask].iterrows():
                    original_value = df_sensors.loc[idx, 'value']
                    if isinstance(original_value, str):
                        if original_value.lower() == 'toxic_gas':
                            df_sensors.loc[idx, 'value'] = 1
                        elif original_value.lower() == 'normal_gas':
                            df_sensors.loc[idx, 'value'] = 0
                        else:
                            df_sensors.loc[idx, 'value'] = 0
                
                # Map sensor types to dashboard categories
                original_sensor_types = df_sensors['sensor_type'].copy()
                df_sensors['sensor_type'] = df_sensors['sensor_type'].map(sensor_type_mapping)
                # Fill NaN values with original sensor_type values
                df_sensors['sensor_type'] = df_sensors['sensor_type'].fillna(original_sensor_types)
                
                # Convert value column to numeric where possible
                df_sensors['value'] = pd.to_numeric(df_sensors['value'], errors='coerce')
                
                # Handle any remaining non-numeric values and invalid data
                df_sensors.loc[df_sensors['value'].isna(), 'value'] = 0
                
                # Fix invalid pH values (negative values are not valid for pH)
                ph_mask = df_sensors['sensor_type'] == 'ph'
                df_sensors.loc[ph_mask & (df_sensors['value'] < 0), 'value'] = 7.0  # Neutral pH
                df_sensors.loc[ph_mask & (df_sensors['value'] > 14), 'value'] = 7.0  # Cap at 14
                
                # Ensure data types are correct
                df_sensors = df_sensors.infer_objects(copy=False)
                
                data_cache["sensor_data"] = df_sensors
                logger.info(f"Loaded {len(df_sensors)} sensor records")
            else:
                logger.warning("No sensor data found in CSV file")
        else:
            logger.warning(f"Sensor data file not found: {data_storage_path}")
        
        
        data_cache["last_update"] = datetime.now()
        
        # Load sensor configuration
        load_sensor_config()
        
        logger.info("Data loaded successfully")
        
    except Exception as e:
        logger.error(f"Error loading data: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")

def get_recent_data(minutes=60, max_records=last_records):
    """Get recent data - always returns latest records for sliding window"""
    if data_cache["sensor_data"].empty:
        logger.info("No sensor data available")
        return pd.DataFrame()
    
    try:
        # Since we're already loading only last rows, use all available data
        # This ensures we always get the latest records (sliding window)
        recent_data = data_cache["sensor_data"].copy()
        
        # Ensure we have exactly the specified number of records or less if data is limited
        if len(recent_data) > max_records:
            recent_data = recent_data.tail(max_records)
        
        logger.info(f"Retrieved {len(recent_data)} records from sensor data (sliding window)")
        
        return recent_data
    except Exception as e:
        logger.error(f"Error in get_recent_data: {e}")
        return pd.DataFrame()

def create_sensor_chart(sensor_type, minutes=60):
    """Create time series chart for specific sensor type"""
    try:
        recent_data = get_recent_data(minutes, max_records=last_records)
        
        if recent_data.empty:
            logger.info("create_sensor_chart - No recent data available")
            fig = go.Figure()
            fig.add_annotation(text="No data available", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
            return fig
        
        sensor_data = recent_data[recent_data['sensor_type'] == sensor_type]
        
        if sensor_data.empty:
            logger.info(f"create_sensor_chart - No data for {sensor_type}")
            fig = go.Figure()
            fig.add_annotation(text=f"No data for {sensor_type}", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
            return fig
        
        fig = go.Figure()
        
        # Group by device_id for different lines (using device_id instead of location)
        for device_id in sensor_data['device_id'].unique():
            device_data = sensor_data[sensor_data['device_id'] == device_id]
            
            fig.add_trace(go.Scatter(
                x=device_data['timestamp'],
                y=device_data['value'],
                mode='lines+markers',
                name=f"{sensor_type.title()} - {device_id}",
                line=dict(width=2),
                marker=dict(size=6)
            ))
        
        # Add threshold lines
        thresholds = get_sensor_thresholds(sensor_type)
        if thresholds:
            # Handle special case for toxic_gas
            if sensor_type == 'toxic_gas':
                # For toxic gas, we don't add threshold lines since it's binary
                pass
            else:
                # Add threshold lines for numeric sensors
                if 'threshold_low' in thresholds and thresholds['threshold_low'] is not None:
                    fig.add_hline(
                        y=thresholds['threshold_low'],
                        line_dash="dash",
                        line_color="red",
                        annotation_text=f"Min: {thresholds['threshold_low']}",
                        annotation_position="bottom right"
                    )
                
                if 'threshold_high' in thresholds and thresholds['threshold_high'] is not None:
                    fig.add_hline(
                        y=thresholds['threshold_high'],
                        line_dash="dash",
                        line_color="red",
                        annotation_text=f"Max: {thresholds['threshold_high']}",
                        annotation_position="top right"
                    )
        
        # Get unit from the data
        unit = sensor_data['unit'].iloc[0] if not sensor_data.empty else ''
        
        fig.update_layout(
            title=f"{sensor_type.title()} Sensor Data",
            xaxis_title="Time",
            yaxis_title=f"{sensor_type.title()} ({unit})",
            hovermode='x unified',
            showlegend=True,
            height=400,
            autosize=False,
            margin=dict(l=50, r=50, t=50, b=50),
            xaxis=dict(
                type='date',
                tickformat='%H:%M:%S',
                tickangle=45,
                fixedrange=True
            ),
            yaxis=dict(fixedrange=True)
        )
        
        return fig
    
    except Exception as e:
        logger.error(f"Error in create_sensor_chart: {e}")
        fig = go.Figure()
        fig.add_annotation(text="Error loading sensor data", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        return fig

def create_multi_sensor_chart(minutes=60):
    """Create multi-sensor overview chart"""
    try:
        recent_data = get_recent_data(minutes, max_records=last_records)
        
        if recent_data.empty:
            logger.info("create_multi_sensor_chart - No recent data available")
            fig = go.Figure()
            fig.add_annotation(text="No data available", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
            return fig
        
        fig = go.Figure()
        
        # Create subplots for each sensor type
        sensor_types = recent_data['sensor_type'].unique()
        
        for i, sensor_type in enumerate(sensor_types):
            sensor_data = recent_data[recent_data['sensor_type'] == sensor_type]
            
            # Normalize values for comparison (0-100 scale)
            if not sensor_data.empty:
                values = sensor_data['value'].values
                # Filter out NaN values
                valid_values = values[~pd.isna(values)]
                if len(valid_values) > 0:
                    min_val, max_val = valid_values.min(), valid_values.max()
                    if max_val > min_val:
                        normalized_values = ((values - min_val) / (max_val - min_val)) * 100
                    else:
                        normalized_values = [50] * len(values)
                    
                    # Handle NaN values in normalized data
                    normalized_values = pd.Series(normalized_values).fillna(50).values
                    
                    fig.add_trace(go.Scatter(
                        x=sensor_data['timestamp'],
                        y=normalized_values,
                        mode='lines+markers',
                        name=sensor_type.title(),
                        line=dict(width=2),
                        marker=dict(size=4)
                    ))
        
        fig.update_layout(
            title="Multi-Sensor Overview",
            xaxis_title="Time",
            yaxis_title="Normalized Value (0-100)",
            hovermode='x unified',
            showlegend=True,
            height=400,
            autosize=False,
            margin=dict(l=50, r=50, t=50, b=50),
            xaxis=dict(
                type='date',
                tickformat='%H:%M:%S',
                tickangle=45,
                fixedrange=True
            ),
            yaxis=dict(
                range=[0, 100],
                fixedrange=True
            )
        )
        
        return fig
    
    except Exception as e:
        logger.error(f"Error in create_multi_sensor_chart: {e}")
        fig = go.Figure()
        fig.add_annotation(text="Error loading multi-sensor data", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        return fig

def create_gauge_chart(sensor_type):
    """Create gauge chart for current sensor value"""
    recent_data = get_recent_data(minutes=5, max_records=50)  # Get last 50 records
    
    if recent_data.empty:
        return go.Figure()
    
    sensor_data = recent_data[recent_data['sensor_type'] == sensor_type]
    
    if sensor_data.empty:
        return go.Figure()
    
    # Get the most recent valid value
    valid_data = sensor_data.dropna(subset=['value'])
    if valid_data.empty:
        return go.Figure()
    
    current_value = valid_data['value'].iloc[-1]
    unit = valid_data['unit'].iloc[0] if not valid_data.empty else ''
    
    # Define gauge range based on sensor type
    if sensor_type == 'atmosphere_temperature':
        min_val, max_val = -10, 50
    elif sensor_type == 'atmosphere_humidity':
        min_val, max_val = 0, 100
    elif sensor_type == 'soil_temperature':
        min_val, max_val = -10, 50
    elif sensor_type == 'soil_moisture':
        min_val, max_val = 0, 100
    elif sensor_type == 'toxic_gas':
        min_val, max_val = 0, 1
    elif sensor_type == 'ph':
        min_val, max_val = 0, 14
    elif sensor_type == 'light':
        min_val, max_val = 0, 100
    else:
        min_val, max_val = 0, 100
    
    # Calculate mean for delta reference
    mean_value = valid_data['value'].mean() if not valid_data.empty else current_value
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=current_value,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': f"{sensor_type.title()} ({unit})"},
        delta={'reference': mean_value},
        gauge={
            'axis': {'range': [min_val, max_val]},
            'bar': {'color': "darkblue"},
            'steps': [
                {'range': [min_val, min_val + (max_val - min_val) * 0.3], 'color': "lightgray"},
                {'range': [min_val + (max_val - min_val) * 0.3, min_val + (max_val - min_val) * 0.7], 'color': "gray"},
                {'range': [min_val + (max_val - min_val) * 0.7, max_val], 'color': "darkgray"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': max_val * 0.9
            }
        }
    ))
    
    fig.update_layout(height=300)
    return fig

def get_local_ip():
    """Get local IP address (Mac/Windows compatible)"""
    try:
        import socket
        import subprocess
        import platform
        
        # Try to get IP address based on OS
        if platform.system() == "Darwin":  # macOS
            try:
                result = subprocess.run(['ipconfig', 'getifaddr', 'en0'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0 and result.stdout.strip():
                    return result.stdout.strip()
            except:
                pass
        
        # Fallback method for all platforms
        try:
            # Connect to a remote address to determine local IP
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
        except:
            pass
        
        # Final fallback
        return "127.0.0.1"
        
    except Exception as e:
        logger.error(f"Error getting local IP: {e}")
        return "127.0.0.1"

def check_broker_status():
    """Check if MQTT broker is running and accessible"""
    try:
        import socket
        import time
        
        # Try to connect to the broker on localhost:1883
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)  # 2 second timeout
        result = sock.connect_ex(('localhost', 1883))
        sock.close()
        
        # Get local IP address
        local_ip = get_local_ip()
        
        if result == 0:
            return f"Active\nIP: {local_ip}\nPort: 1883"  # Broker is running
        else:
            return f"Inactive\nIP: {local_ip}\nPort: 1883"  # Broker is not accessible
            
    except Exception as e:
        logger.error(f"Error checking broker status: {e}")
        local_ip = get_local_ip()
        return f"Error\nIP: {local_ip}\nPort: 1883"

def get_system_status():
    """Get current system status - checks if MQTT broker is running"""
    return check_broker_status()

def create_current_values_display():
    """Create current values display for all sensors"""
    try:
        recent_data = get_recent_data(minutes=5, max_records=50)
        
        if recent_data.empty:
            logger.info("create_current_values_display - No data available")
            return html.Div("No data available", className="no-data")
    except Exception as e:
        logger.error(f"Error in create_current_values_display: {e}")
        return html.Div("Error loading current values", className="no-data")
    
    # Define sensor display order and labels
    sensor_display = {
        'atmosphere_temperature': {'label': 'Atmosphere Temperature', 'icon': '🌡️'},
        'atmosphere_humidity': {'label': 'Atmosphere Humidity', 'icon': '💧'},
        'soil_temperature': {'label': 'Soil Temperature', 'icon': '🌱'},
        'soil_moisture': {'label': 'Soil Moisture', 'icon': '💦'},
        'toxic_gas': {'label': 'Toxic Gas', 'icon': '⚠️'},
        'ph': {'label': 'pH Level', 'icon': '🧪'},
        'light': {'label': 'Ambient', 'icon': '💡'}
    }
    
    current_values = []
    
    for sensor_type, info in sensor_display.items():
        sensor_data = recent_data[recent_data['sensor_type'] == sensor_type]
        
        if not sensor_data.empty:
            # Get the most recent valid value
            valid_data = sensor_data.dropna(subset=['value'])
            if not valid_data.empty:
                latest_value = valid_data['value'].iloc[-1]
                unit = valid_data['unit'].iloc[0]
                timestamp = valid_data['timestamp'].iloc[-1]
                
                # Format the value based on sensor type
                if sensor_type == 'light':
                    display_value = "light" if latest_value > 0 else "dark"
                elif sensor_type == 'toxic_gas':
                    display_value = "toxic_gas" if latest_value > 0 else "normal_gas"
                else:
                    display_value = f"{latest_value:.2f} {unit}"
                
                current_values.append(
                    html.Div([
                        html.Div([
                            html.Span(info['icon'], className="sensor-icon"),
                            html.H4(info['label'], className="sensor-label"),
                            html.P(display_value, className="sensor-value"),
                            html.P(f"Updated: {timestamp.strftime('%H:%M:%S')}", className="sensor-time")
                        ], className="sensor-card")
                    ], className="sensor-item")
                )
    
    # If no current values found, show a simple message
    if not current_values:
        return html.Div([
            html.H4("No current sensor data available"),
            html.P("Please check if sensors are connected and sending data.")
        ], className="no-data")
    
    return html.Div(current_values, className="current-values-grid")

def create_threshold_info(sensor_type):
    """Create threshold information display for a sensor type"""
    try:
        thresholds = get_sensor_thresholds(sensor_type)
        
        if not thresholds:
            return html.Div("", className="threshold-info")
        
        # Handle special cases
        if sensor_type == 'toxic_gas':
            return html.Div([
                html.H4("Threshold Information", className="threshold-title"),
                html.P(f"Warning Level: {thresholds.get('threshold_warning', 'toxic_gas')}", className="threshold-text"),
                html.P(f"Ideal Range: {thresholds.get('ideal_range', 'normal_gas')}", className="threshold-text")
            ], className="threshold-info")
        elif sensor_type == 'light':
            return html.Div("", className="threshold-info")  # No thresholds for light
        else:
            # For numeric sensors
            threshold_text = []
            if 'threshold_low' in thresholds and thresholds['threshold_low'] is not None:
                threshold_text.append(f"Minimum: {thresholds['threshold_low']}")
            if 'threshold_high' in thresholds and thresholds['threshold_high'] is not None:
                threshold_text.append(f"Maximum: {thresholds['threshold_high']}")
            if 'ideal_range' in thresholds and thresholds['ideal_range']:
                threshold_text.append(f"Ideal Range: {thresholds['ideal_range']}")
            
            if threshold_text:
                return html.Div([
                    html.H4("Threshold Information", className="threshold-title"),
                    html.P(" | ".join(threshold_text), className="threshold-text")
                ], className="threshold-info")
            else:
                return html.Div("", className="threshold-info")
                
    except Exception as e:
        logger.error(f"Error creating threshold info: {e}")
        return html.Div("", className="threshold-info")


# Define app layout
app.layout = html.Div([
    html.Div([
        html.H1("IoT Dashboard", className="header-title"),
        html.Div([
            html.Div([
                html.H3("Broker Status", className="status-title"),
                html.Div(id="system-status", className="status-indicator")
            ], className="status-card"),
            html.Div([
                html.H3("Last Update", className="status-title"),
                html.Div(id="last-update", className="status-indicator")
            ], className="status-card"),
            html.Div([
                html.H3("Window Size", className="status-title"),
                html.Div(f"{last_records} Records", className="status-indicator")
            ], className="status-card")
        ], className="status-row")
    ], className="header"),
    
    html.Div([
        html.Div([
            html.H3("📊 Multi-Sensor Overview"),
            dcc.Graph(id="multi-sensor-chart")
        ], className="chart-container"),
        
        html.Div([
            html.H3("📈 Individual Sensor Charts"),
            html.Div([
                dcc.Dropdown(
                    id="sensor-type-dropdown",
                    options=[
                        {'label': 'Atmosphere Temperature', 'value': 'atmosphere_temperature'},
                        {'label': 'Atmosphere Humidity', 'value': 'atmosphere_humidity'},
                        {'label': 'Soil Temperature', 'value': 'soil_temperature'},
                        {'label': 'Soil Moisture', 'value': 'soil_moisture'},
                        {'label': 'Toxic Gas', 'value': 'toxic_gas'},
                        {'label': 'pH', 'value': 'ph'},
                        {'label': 'Ambient', 'value': 'light'}
                    ],
                    value='atmosphere_temperature',
                    className="sensor-dropdown"
                ),
                dcc.Graph(id="sensor-chart"),
                html.Div(id="threshold-info", className="threshold-info")
            ], className="sensor-chart-container")
        ], className="chart-container")
    ], className="charts-section"),
    
    html.Div([
        html.H3("🎯 Current Values"),
        html.Div(id="current-values", className="current-values-container")
    ], className="current-values-section"),
    
    
    # Auto-refresh component
    dcc.Interval(
        id='interval-component',
        interval=3*1000,  # Update every 3 seconds for better sliding window effect
        n_intervals=0
    )
], className="dashboard")

# CSS styling
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0;
                padding: 0;
                background-color: #f5f5f5;
            }
            .dashboard {
                max-width: 1400px;
                margin: 0 auto;
                padding: 20px;
            }
            .header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 30px;
                border-radius: 15px;
                margin-bottom: 30px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            }
            .header-title {
                margin: 0 0 20px 0;
                font-size: 2.5em;
                text-align: center;
            }
            .status-row {
                display: flex;
                gap: 20px;
                justify-content: center;
            }
            .status-card {
                background: rgba(255,255,255,0.1);
                padding: 15px 25px;
                border-radius: 10px;
                text-align: center;
                min-width: 150px;
            }
            .status-title {
                margin: 0 0 10px 0;
                font-size: 1.1em;
                opacity: 0.9;
            }
            .status-indicator {
                font-size: 1.3em;
                font-weight: bold;
            }
            .status-indicator.connected {
                color: #28a745;
            }
            .status-indicator.disconnected {
                color: #dc3545;
            }
            .status-indicator.recently-active {
                color: #ffc107;
            }
            .status-indicator.error {
                color: #6c757d;
            }
            .status-indicator.active {
                color: #28a745;
            }
            .status-indicator.inactive {
                color: #dc3545;
            }
            .status-container {
                text-align: center;
            }
            .status-main {
                font-size: 1.1em;
                font-weight: bold;
                margin-bottom: 5px;
            }
            .status-main.active {
                color: #28a745;
            }
            .status-main.inactive {
                color: #dc3545;
            }
            .status-main.error {
                color: #6c757d;
            }
            .status-details {
                font-size: 0.9em;
                color: #666;
                line-height: 1.3;
            }
            .charts-section {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 30px;
                margin-bottom: 30px;
            }
            .chart-container {
                background: white;
                padding: 25px;
                border-radius: 15px;
                box-shadow: 0 5px 15px rgba(0,0,0,0.1);
                height: 500px;
                overflow: hidden;
            }
            .chart-container h3 {
                margin: 0 0 20px 0;
                color: #333;
                font-size: 1.4em;
            }
            .sensor-chart-container {
                margin-top: 15px;
            }
            .sensor-dropdown {
                margin-bottom: 15px;
            }
            .current-values-section {
                background: white;
                padding: 25px;
                border-radius: 15px;
                box-shadow: 0 5px 15px rgba(0,0,0,0.1);
                margin-bottom: 30px;
            }
            .current-values-section h3 {
                margin: 0 0 20px 0;
                color: #333;
                font-size: 1.4em;
            }
            .current-values-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
            }
            .sensor-card {
                background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
                padding: 20px;
                border-radius: 12px;
                border-left: 4px solid #667eea;
                text-align: center;
                transition: transform 0.2s ease;
            }
            .sensor-card:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            }
            .sensor-icon {
                font-size: 2em;
                display: block;
                margin-bottom: 10px;
            }
            .sensor-label {
                margin: 0 0 10px 0;
                color: #333;
                font-size: 1.1em;
                font-weight: 600;
            }
            .sensor-value {
                margin: 0 0 5px 0;
                color: #667eea;
                font-size: 1.3em;
                font-weight: bold;
            }
            .sensor-time {
                margin: 0;
                color: #666;
                font-size: 0.9em;
            }
            .no-data {
                text-align: center;
                color: #666;
                font-style: italic;
                padding: 40px;
            }
            .summary-section {
                background: white;
                padding: 25px;
                border-radius: 15px;
                box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            }
            .summary-section h3 {
                margin: 0 0 20px 0;
                color: #333;
                font-size: 1.4em;
            }
            .summary-container {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
            }
            .summary-item {
                background: #f8f9fa;
                padding: 15px;
                border-radius: 10px;
                border-left: 4px solid #667eea;
            }
            .summary-item h4 {
                margin: 0 0 5px 0;
                color: #333;
            }
            .summary-item p {
                margin: 0;
                color: #666;
            }
            .js-plotly-plot {
                height: 400px !important;
                max-height: 400px !important;
            }
            .threshold-info {
                margin-top: 15px;
                padding: 15px;
                background: #f8f9fa;
                border-radius: 8px;
                border-left: 4px solid #dc3545;
            }
            .threshold-title {
                margin: 0 0 10px 0;
                color: #dc3545;
                font-size: 1.1em;
                font-weight: 600;
            }
            .threshold-text {
                margin: 5px 0;
                color: #495057;
                font-size: 0.95em;
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

# Callbacks
@app.callback(
    [Output('multi-sensor-chart', 'figure'),
     Output('sensor-chart', 'figure'),
     Output('current-values', 'children'),
     Output('system-status', 'children'),
     Output('last-update', 'children'),
     Output('threshold-info', 'children')],
    [Input('interval-component', 'n_intervals'),
     Input('sensor-type-dropdown', 'value')]
)
def update_dashboard(n_intervals, selected_sensor):
    """Update dashboard components"""
    try:
        # Reload data
        load_data()
        
        # Debug logging
        logger.info(f"Dashboard update - intervals: {n_intervals}, sensor: {selected_sensor}")
        
        # Create charts with error handling
        try:
            multi_chart = create_multi_sensor_chart()
        except Exception as e:
            logger.error(f"Error creating multi-sensor chart: {e}")
            multi_chart = go.Figure()
            multi_chart.add_annotation(text="Error loading multi-sensor data", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        
        try:
            sensor_chart = create_sensor_chart(selected_sensor)
        except Exception as e:
            logger.error(f"Error creating sensor chart: {e}")
            sensor_chart = go.Figure()
            sensor_chart.add_annotation(text="Error loading sensor data", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        
        # Create current values display with error handling
        try:
            current_values = create_current_values_display()
        except Exception as e:
            logger.error(f"Error creating current values: {e}")
            current_values = html.Div("Error loading current values", className="no-data")
        
        # Create threshold information display
        try:
            threshold_info = create_threshold_info(selected_sensor)
        except Exception as e:
            logger.error(f"Error creating threshold info: {e}")
            threshold_info = html.Div("", className="threshold-info")
        
        
        # Get system status with error handling
        try:
            system_status = get_system_status()
            # Parse the status to separate status and details
            lines = system_status.split('\n')
            status_text = lines[0]  # Active/Inactive/Error
            details = '\n'.join(lines[1:])  # IP: and Port: lines
            
            # Apply CSS class based on status
            if "Active" in status_text:
                system_status_display = html.Div([
                    html.Div(status_text, className="status-main active"),
                    html.Div(details, className="status-details")
                ], className="status-container")
            elif "Inactive" in status_text:
                system_status_display = html.Div([
                    html.Div(status_text, className="status-main inactive"),
                    html.Div(details, className="status-details")
                ], className="status-container")
            else:
                system_status_display = html.Div([
                    html.Div(status_text, className="status-main error"),
                    html.Div(details, className="status-details")
                ], className="status-container")
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            system_status_display = html.Div([
                html.Div("Error", className="status-main error"),
                html.Div("Unable to get status", className="status-details")
            ], className="status-container")
        
        
        try:
            last_update = data_cache["last_update"].strftime('%H:%M:%S') if data_cache["last_update"] else "Never"
        except Exception as e:
            logger.error(f"Error formatting last update: {e}")
            last_update = "Unknown"
        
        return (multi_chart, sensor_chart, current_values, 
                system_status_display, last_update, threshold_info)
    
    except Exception as e:
        logger.error(f"Critical error in update_dashboard: {e}")
        # Return empty/default values for all outputs
        empty_fig = go.Figure()
        empty_fig.add_annotation(text="Error loading data", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        
        return (empty_fig, empty_fig, html.Div("Error loading data", className="no-data"), 
                html.Span("Error", className="status-indicator error"), "Unknown", html.Div("", className="threshold-info"))


if __name__ == "__main__":
    # Load initial data
    load_data()
    
    # Run the app
    app.run(debug=True, host='0.0.0.0', port=8050)