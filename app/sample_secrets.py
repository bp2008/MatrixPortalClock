# This file is where you keep secret settings, passwords, and tokens!
# If you put them in the code you risk committing that info or sharing it

# RENAME FILE TO secrets.py and fill in your own data as needed

secrets = {
    "ssid" : '',
    "password" : '', # WiFi password
    "mqttbroker" : "", # IP address recommended. DNS lookup is a bit flakey in my experience
    "mqttport" : 1883,
    "mqttuser" : "",
    "mqttpass" : "",
    "color_nowifi" : (51, 0, 0), # Neopixel on the back will be this color while WiFi is not connected.
    "color_wifi" : (0, 0, 0), # Neopixel on the back will be this color while WiFi is connected.
    "matrix_portal_id" : "1" # Change this string if you run multiple clocks with this software and want them to load different strings from MQTT.
    }
