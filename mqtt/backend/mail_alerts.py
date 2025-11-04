#!/usr/bin/env python3
"""
Mail Alerts System
Checks sensor data against thresholds and sends email alerts

nable 2-Factor Authentication on your Gmail account
Generate App Password:
Go to Google Account → Security → 2-Step Verification
Click "App passwords"
Select "Mail" and generate password
Use this 16-character password in mail_alerts.py


⚠️ Alert Messages with Thresholds
🌱 Soil Moisture

Ideal Range: 20% – 80%

🔻 Low Moisture Alert (Moisture < 20%)

Alert: Soil moisture level is below 20%.
This may cause irreversible damage to the plant. Please inspect and irrigate immediately.

🔺 High Moisture Alert (Moisture > 80%)

Alert: Soil moisture level exceeds 80%.
Excess moisture deprives roots of oxygen, can lead to rot and disease, and hinders nutrient and water uptake. Please take corrective action.

⚗️ Soil pH

Ideal Range: 6.5 – 7.5

🔻 Low pH Alert (pH < 6.5)

Alert: Soil pH is below 6.5.
This may cause irreversible damage to the plant. Please test and amend the soil to raise pH.

🔺 High pH Alert (pH > 7.0)

Alert: Soil pH is above 7.0.
High pH levels hinder nutrient and water uptake. Please test and adjust the soil pH accordingly.

🌡️ Air Temperature

Ideal Range: 18°C – 25°C

❗ Air Temperature Alert (Temp < 18°C or > 25°C)

Alert: Ambient air temperature is outside the optimal range (18–25°C).
Extreme temperatures can stress the plant. Please monitor and take protective measures.

💧 Air Humidity

Ideal Range: 40% – 80%

❗ Air Humidity Alert (Humidity < 40% or > 80%)

Alert: Ambient humidity is outside the optimal range (40–80%).
Low or high humidity may affect plant health. Please assess and adjust environmental conditions if necessary.

☠️ Toxic Gas Detection

Condition: toxic_gas = true

☢️ Toxic Gas Alert

Alert: Toxic gas has been detected in the environment.
Immediate attention required to protect plants and ensure safety.

🌞 Light Condition

Status: light or dark

No alerts are issued based on light conditions.

If any of the sensor reading is out of the ideal range, the system will send an email alert.


"""

import json
import csv
import smtplib
import logging
import time
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from config import config

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MailAlerts:
    def __init__(self):
        # Email configuration (you can add these to config.json if needed)
        self.smtp_server = "smtp.gmail.com"  # Change to your SMTP server
        self.smtp_port = 587
        self.sender_email = "iotprojectsem7@gmail.com"  # Change to your email
        self.sender_password = "zhbf ttww luhp nrpg"  # Gmail App Password
        self.recipient_email = "pamulapati.jr24@gmail.com"#  # Change to recipient email
        
        # Load sensor thresholds from config
        self.sensor_thresholds = config.SENSOR_TYPES
        
    def get_latest_sensor_data(self, limit=10):
        """Get the latest sensor data from CSV file"""
        try:
            sensor_data_file = config.get_sensor_data_file()
            data = []
            
            with open(sensor_data_file, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                rows = list(reader)
                
                # Get the latest data and convert to dict format
                latest_rows = rows[-limit:] if limit else rows
                
                for row in latest_rows:
                    if len(row) >= 6:  # Ensure we have all required fields
                        data.append({
                            'timestamp': row[0],
                            'sensor_id': row[1],
                            'sensor_type': row[2],
                            'value': row[3],
                            'unit': row[4],
                            'location': row[5]
                        })
                
            return data
            
        except Exception as e:
            logger.error(f"Error reading sensor data: {e}")
            return []
    
    def check_threshold_violations(self, sensor_data):
        """Check if sensor data violates thresholds"""
        violations = []
        
        for data in sensor_data:
            sensor_type = data.get('sensor_type', '')
            value = data.get('value', '')
            timestamp = data.get('timestamp', '')
            sensor_id = data.get('sensor_id', '')
            location = data.get('location', '')
            
            # Skip if no sensor type or value
            if not sensor_type or not value:
                continue
                
            # Get threshold configuration for this sensor type
            threshold_config = self.sensor_thresholds.get(sensor_type, {})
            
            if not threshold_config:
                continue
                
            violation = None
            
            # Check for gas sensor (string comparison)
            if sensor_type == 'gas_sensor':
                threshold_warning = threshold_config.get('threshold_warning')
                if threshold_warning and value == threshold_warning:
                    alert_msg = threshold_config.get('alert_conditions', {}).get('toxic_gas', 
                        f"Gas sensor detected {value} - {threshold_warning} condition!")
                    violation = {
                        'sensor_id': sensor_id,
                        'sensor_type': sensor_type,
                        'value': value,
                        'threshold': threshold_warning,
                        'timestamp': timestamp,
                        'location': location,
                        'message': alert_msg
                    }
            
            # Check for numeric sensors with low and high thresholds
            elif sensor_type in ['soil_temp_sensor', 'moisture_sensor', 'ph_sensor', 'air_temp_sensor', 'air_hum_sensor']:
                try:
                    numeric_value = float(value)
                    threshold_low = threshold_config.get('threshold_low')
                    threshold_high = threshold_config.get('threshold_high')
                    alert_conditions = threshold_config.get('alert_conditions', {})
                    
                    # Check for low threshold violation
                    if threshold_low is not None and numeric_value < threshold_low:
                        alert_msg = alert_conditions.get('low', 
                            f"{sensor_type.replace('_', ' ').title()} reading {numeric_value} is below threshold {threshold_low}!")
                        violation = {
                            'sensor_id': sensor_id,
                            'sensor_type': sensor_type,
                            'value': numeric_value,
                            'threshold': f"< {threshold_low}",
                            'timestamp': timestamp,
                            'location': location,
                            'message': alert_msg
                        }
                    
                    # Check for high threshold violation
                    elif threshold_high is not None and numeric_value > threshold_high:
                        alert_msg = alert_conditions.get('high', 
                            f"{sensor_type.replace('_', ' ').title()} reading {numeric_value} is above threshold {threshold_high}!")
                        violation = {
                            'sensor_id': sensor_id,
                            'sensor_type': sensor_type,
                            'value': numeric_value,
                            'threshold': f"> {threshold_high}",
                            'timestamp': timestamp,
                            'location': location,
                            'message': alert_msg
                        }
                        
                except (ValueError, TypeError):
                    logger.warning(f"Could not convert value '{value}' to number for sensor {sensor_type}")
                    continue
            
            # Check for light sensor (special case - no alerts)
            elif sensor_type == 'light_sensor':
                # Light sensor has no alert conditions as per documentation
                continue
            
            if violation:
                violations.append(violation)
                logger.warning(f"Threshold violation detected: {violation['message']}")
        
        return violations
    
    def send_email_alert(self, violations):
        """Send email alert for threshold violations"""
        if not violations:
            logger.info("No threshold violations found")
            return False
            
        try:
            # Create email message
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = self.recipient_email
            msg['Subject'] = f"🚨 Sensor Alert: {len(violations)} Threshold Violation(s) Detected"
            
            # Create email body
            body = f"""
            <h2>🚨 Sensor Threshold Violations Detected</h2>
            <p><strong>Alert Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p><strong>Total Violations:</strong> {len(violations)}</p>
            
            <h3>Violation Details:</h3>
            <table border="1" style="border-collapse: collapse; width: 100%;">
                <tr style="background-color: #f2f2f2;">
                    <th>Sensor ID</th>
                    <th>Sensor Type</th>
                    <th>Value</th>
                    <th>Threshold</th>
                    <th>Location</th>
                    <th>Timestamp</th>
                </tr>
            """
            
            for violation in violations:
                body += f"""
                <tr>
                    <td>{violation['sensor_id']}</td>
                    <td>{violation['sensor_type'].replace('_', ' ').title()}</td>
                    <td><strong style="color: red;">{violation['value']}</strong></td>
                    <td>{violation['threshold']}</td>
                    <td>{violation['location']}</td>
                    <td>{violation['timestamp']}</td>
                </tr>
                """
            
            body += """
            </table>
            
            <h3>Action Required:</h3>
            <ul>
                <li>Check the affected sensors immediately</li>
                <li>Verify sensor readings and calibration</li>
                <li>Take appropriate corrective action</li>
                <li>Monitor the situation closely</li>
            </ul>
            
            <p><em>This is an automated alert from the MQTT Sensor Monitoring System.</em></p>
            """
            
            msg.attach(MIMEText(body, 'html'))
            
            # Send email
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.sender_email, self.sender_password)
            
            text = msg.as_string()
            server.sendmail(self.sender_email, self.recipient_email, text)
            server.quit()
            
            logger.info(f"Email alert sent successfully for {len(violations)} violations")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
            return False
    
    def check_and_alert(self):
        """Main method to check sensor data and send alerts if needed"""
        logger.info("Checking sensor data for threshold violations...")
        
        # Get latest sensor data
        latest_data = self.get_latest_sensor_data(limit=7)  # Check last 7 readings
        
        if not latest_data:
            logger.warning("No sensor data found")
            return
        
        logger.info(f"Checking {len(latest_data)} latest sensor readings")
        
        # Check for threshold violations
        violations = self.check_threshold_violations(latest_data)
        
        if violations:
            logger.warning(f"Found {len(violations)} threshold violations")
            
            # Print violations to console
            for violation in violations:
                print(f"🚨 ALERT: {violation['message']}")
                print(f"   Sensor: {violation['sensor_id']} ({violation['sensor_type']})")
                print(f"   Value: {violation['value']} (Threshold: {violation['threshold']})")
                print(f"   Location: {violation['location']}")
                print(f"   Time: {violation['timestamp']}")
                print("-" * 50)
            
            # Send email alert
            self.send_email_alert(violations)
        else:
            logger.info("No threshold violations found - all sensors within normal range")

def run_continuous_monitoring(check_interval=60):
    """Run continuous monitoring with specified interval"""
    alerts = MailAlerts()
    logger.info(f"🚀 Starting Continuous Monitoring - Checking every {check_interval} seconds")
    logger.info(f"📧 Email alerts will be sent to: {alerts.recipient_email}")
    logger.info("🛑 Press Ctrl+C to stop the service")
    print("=" * 60)
    
    try:
        while True:
            try:
                # Run the alert check
                logger.info(f"🔍 [{datetime.now().strftime('%H:%M:%S')}] Checking sensor data...")
                alerts.check_and_alert()
                
                # Wait for next check
                logger.info(f"⏰ Waiting {check_interval} seconds until next check...")
                time.sleep(check_interval)
                
            except KeyboardInterrupt:
                logger.info("🛑 Monitoring stopped by user")
                break
            except Exception as e:
                logger.error(f"❌ Error in monitoring: {e}")
                logger.info(f"⏰ Retrying in {check_interval} seconds...")
                time.sleep(check_interval)
                
    except KeyboardInterrupt:
        logger.info("🛑 Continuous Monitoring Stopped")

def main():
    """Main function to run the alert system"""
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        if command == 'continuous' or command == 'monitor':
            # Run continuous monitoring
            interval = 60  # Default 60 seconds
            if len(sys.argv) > 2:
                try:
                    interval = int(sys.argv[2])
                except ValueError:
                    print("❌ Invalid interval. Using default 60 seconds.")
            
            run_continuous_monitoring(interval)
        elif command == 'once' or command == 'check':
            # Run once
            alerts = MailAlerts()
            alerts.check_and_alert()
        else:
            print("Usage: python3 mail_alerts.py [continuous|once] [interval]")
            print("  continuous [interval] - Run continuous monitoring (default: 60 seconds)")
            print("  once                - Check once and exit")
    else:
        # Default: run once
        alerts = MailAlerts()
        alerts.check_and_alert()

if __name__ == "__main__":
    main()
