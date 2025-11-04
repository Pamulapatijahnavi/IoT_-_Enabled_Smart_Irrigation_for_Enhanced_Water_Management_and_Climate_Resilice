# MQTT IoT Data Collection & Visualization System

STEP1 
Check for the private IP , assigned by your Wi-Fi router.

dineshe@mac mqtt % ipconfig getifaddr en0

192.168.0.97

broker can be accessed via this ip address and its port mqtt_port = 1883 , Configure this in the Esp32 Code.


==========
the sensor data last 6 hours will be backed up in the backup folder in data, 
backup_1, 
backup_2, 

it can be used or deleted.

===================== 
Quick Test

# Terminal 1: Start MQTT Broker
cd /Users/dineshe/Documents/Learning/mqtt
mosquitto -c broker/mosquitto.conf


# Terminal 3: Start MQTT Subscriber (to see data being received)
cd /Users/dineshe/Documents/Learning/mqtt
source venv/bin/activate
python3 backend/mqtt_subscriber.py

# Terminal 4 : start the alert system
cd /Users/dineshe/Documents/Learning/mqtt
source venv/bin/activate
python3 backend/mail_alerts.py     // For one time

For continous service 

cd /Users/dineshe/Documents/Learning/mqtt/backend
python3 backend/mail_alerts.py continuous        



# Terminal 4: Start Web Dashboard
cd /Users/dineshe/Documents/Learning/mqtt
source venv/bin/activate
python3 dashboard/app.py


---------------------
  to run activate the virtual enviroment to  we neet to excute in ter -------
PS D:\mqtt> Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
PS D:\mqtt> .\venv\Scripts\Activate


-----------------------
to start the mosquitto broker ------broker

& "C:\Program Files\mosquitto\mosquitto.exe" -c D:\mqtt\broker\mosquitto.conf

----------------------------
to start the subscriber

python backend/mqtt_subscriber.py

-----------------------
now to start the webapplication

python dashboard/app.py

----------------------
start the alert system
python backend/mail_alerts.py 


python backend/mail_alerts.py continuous
