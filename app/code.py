import time
import board
import busio
import displayio
import neopixel
from digitalio import DigitalInOut
from adafruit_esp32spi import adafruit_esp32spi
import adafruit_connection_manager
import adafruit_minimqtt.adafruit_minimqtt as MQTT
import rtc
import re
import supervisor
import microcontroller
import storage
import traceback

# Clock-related imports
from adafruit_matrixportal.matrix import Matrix
from adafruit_display_text.label import Label
from scrolling_label import ScrollingLabel
#from vertical_scrolling_label import VerticalScrollingLabel
from adafruit_bitmap_font import bitmap_font

### Display setup ###
matrix = Matrix(width=64, height=32, bit_depth=4)
display = matrix.display

group = displayio.Group()
display.root_group = group

### Load Secrets ###
try:
    from secrets import secrets
except ImportError:
    print("secrets.py not found")
    raise

### Configure Status LED ###
color_nowifi = secrets["color_nowifi"]
color_wifi = secrets["color_wifi"]
status_light = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=1)
status_light.fill(color_nowifi)
status_light.fill(color_nowifi)  # First call sometimes sets the wrong color


### Text setup ###
def MakeLabel(font, color, x, y, scrollAfter=0):
    if scrollAfter:
        lbl = ScrollingLabel(font,
                             max_characters=scrollAfter,
                             animate_time=0.2,
                             tab_replacement=(1, " "))
    else:
        lbl = Label(font, tab_replacement=(2, " "))
    lbl.color = color
    lbl.x = x
    lbl.y = y
    group.append(lbl)
    return lbl


clockFont = bitmap_font.load_font("/IBMPlexMono-Medium-24_jep-modified2.pcf")
# clockFont character size is 14x25. Most actually use 12x17.
smallFont = bitmap_font.load_font("tom-thumb-modified.pcf")
# smallFont character size is 6x4 including spincluding spacing between chars. Some characters extend a little into the spacing area on bottom and right edges.

clock_label = MakeLabel(clockFont, 0xFFFF00, 0, 9)
small_label1 = MakeLabel(smallFont, 0x1F0000, 0, display.height - 9, 16)
small_label2 = MakeLabel(smallFont, 0x200000, 0, display.height - 3, 16)
#crashDumpLabel = VerticalScrollingLabel(smallFont, max_characters=16, max_lines=5)
#crashDumpLabel.color = 0xFF0000
#crashDumpLabel.x = 0
#crashDumpLabel.y = 3
#crashDumpLabel.background_color = 0x000000
#group.append(crashDumpLabel)

clock_label.text = ""
small_label2.full_text = "LOADING FONTS"

# As of this writing, glyphs do not load reliably from pcf fonts if used in a scrolling label, unless all characters are preloaded. So we'll do that now
Label(
    smallFont
).text = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz01234567890-=!@#$%^&*()_+[]{}\\|;:'\",.<>/?`~"
Label(clockFont).text = "01234567890:"

small_label2.full_text = "LOADING"

### Setup Color-matching regex ###
rxFindColorTag = re.compile(
    "^#([0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f])#")

### Configure ESP chip (for WiFi) ###
esp32_cs = DigitalInOut(board.ESP_CS)
esp32_ready = DigitalInOut(board.ESP_BUSY)
esp32_reset = DigitalInOut(board.ESP_RESET)

spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)

### Methods ###
time_offset = 0  # When this offset is added to (time.monotonic_ns() / 1000000), the result is the current unix epoch time in milliseconds.
lastTimesync = -9999999


def ScrollLabel(lbl):
    if len(lbl.full_text) > 16:
        lbl.update(True)


def exprint(e, includeStack=False, singleLine=False):
    if includeStack:
        #fullMsg = type(e).__name__ + ": " + str(e)
        fullMsg = '\n'.join(traceback.format_exception(type(e), e, e.__traceback__))
        fullMsg = fullMsg.replace("\t", "  ")
        if singleLine:
            #fullMsg = fullMsg.replace("\r\n", "  ")
            #fullMsg = fullMsg.replace("\r", "  ")
            fullMsg = fullMsg.replace("\n", "  ")
        #else:
            #fullMsg = fullMsg.replace("\r\n", "\n").replace("\r", "\n")
        return fullMsg
    else:
        return type(e).__name__ + ": " + str(e)


def loop_n_sec(n):
    for _ in range(round(n * 5)):
        time.sleep(0.2)
        clockUpdate()
        ScrollLabel(small_label1)
        ScrollLabel(small_label2)


#def is_usb_connected():
#    try:
#        storage.remount('/', readonly=False)  # attempt to mount readwrite
#        storage.remount('/', readonly=True)  # attempt to mount readonly
#    except RuntimeError as e:
#        return True
#    return False

#is_usb = "CONNECTED" if is_usb_connected() else "NOT CONNECTED"
#print("USB is " + is_usb)

if supervisor.runtime.usb_connected:
    print("USB is connected")
else:
    print("USB is NOT connected")


def writeErrorFile(message):
    if not supervisor.runtime.usb_connected:
        try:
            storage.remount('/', readonly=False)
        except RuntimeError as e:
            return
        with open('LastError.txt', 'w') as f:
            now = 0
            try:
                now = time.localtime(bptime())  # Get the time values we need
            except OverflowError as e:
                now = time.localtime()
            f.write(timeToDateString(now))
            f.write("\n")
            f.write(message)
    else:
        print("USB is connected. Will not write error file.")


def timeToDateString(t: time.struct_time):
    hours = t[3]
    tt = "AM"
    if hours > 12:  # Handle times later than 12:59
        hours -= 12
        tt = "PM"
    elif not hours:  # Handle times between 0:00 and 0:59
        hours = 12
    return "{yy:02d}-{MM:02d}-{dd:02d} {hh}:{mm:02d}:{ss:02d} {tt}".format(
        yy=t[0], MM=t[1], dd=t[2], hh=hours, mm=t[4], ss=t[5], tt=tt)


def bptime():
    """Returns the local time in integer seconds since the unix epoch. Uses the global variable time_offset to store the offset."""
    return ((time.monotonic_ns() // 1000000) + time_offset) // 1000


def bptime_learn_epochms(epochms):
    """Given the integer milliseconds since the unix epoch in local time, this function sets the time offset necessary for bptime() to return the correct time."""
    global time_offset  # Tell python to refer to the global variable when setting time_offset
    time_offset = epochms - (time.monotonic_ns() // 1000000)


def performance_now():
    """Returns a monotonic timestamp in milliseconds since device startup."""
    return time.monotonic_ns() // 1000000


def setSuccess(message):
    setLabel(2, message, 0x00FF00)


def setInfo(message):
    setLabel(2, message, 0x00FFFF)


def setWarning(message):
    setLabel(2, message, 0xFFFF00)


def setError(message):
    setLabel(2, message, 0xFF0000)


def setLabel(lineNumber, message, color):
    if message == "" or message == None:
        message = " "

    if lineNumber == 1:
        lbl = small_label1
    elif lineNumber == 2:
        lbl = small_label2

    lbl.full_text = message

    if color:
        lbl.color = color


def setLabelFromMqtt(lineNumber, message):
    if message == "" or message == None:
        message = " "
    match = rxFindColorTag.match(message)
    if match != None:
        color = int(match.group(1), 16)
        message = message[8:]
    else:
        color = 0x666666
    setLabel(lineNumber, message, color)


def setstatus(msg1, msg2, msg3):
    if msg2:
        print(msg1 + ": " + msg2)
        if msg3:
            print(msg3)
    else:
        print(msg1)
    small_label1.text = msg1
    small_label2.text = msg2


def maintainWifi():
    """Makes one attempt to connect to wifi (if necessary). Returns True if connected, False if not connected."""
    if not esp.is_connected:
        try:
            print("Connecting WiFi")
            setInfo("Connecting WiFi")

            esp.connect_AP(secrets["ssid"], secrets["password"])
            status_light.fill(color_wifi)

            print("Connected WiFi to", str(esp.ssid, "utf-8"), "with RSSI:",
                  esp.rssi)
            setSuccess("WiFi Connected")

            try:
                mqtt_client.disconnect()
            except (ValueError, RuntimeError, ConnectionError, TimeoutError,
                    MQTT.MMQTTException) as e:
                pass
        except (RuntimeError, ConnectionError, TimeoutError) as e:
            print("WiFi Connect Failed: " + exprint(e))
            setError("WiFi Connect Failed: " + exprint(e))
            status_light.fill(color_nowifi)
            status_light.fill(color_nowifi)
            return False
    status_light.fill(color_wifi)
    return True


def maintainMqtt():
    """Reconnects to MQTT if necessary and checks for messages from MQTT. Returns True if succesful, False if not connected"""
    try:
        # Connect if needed
        if not mqtt_client.is_connected():
            print("Connecting MQTT")
            setInfo("Connecting MQTT")

            try:
                mqtt_client.reconnect(resub_topics=False)
            except (ValueError, RuntimeError, ConnectionError, TimeoutError,
                    MQTT.MMQTTException) as e:
                print("Failed to connect to MQTT: " + exprint(e))
                setError("MQTT CONN FAIL: " + exprint(e))
                loop_n_sec(15)
                setError("WiFi Reconnect")
                dropWifi()
                #if type(e).__name__ == "RuntimeError" and str(e) == "Failed to request hostname":
                return False

            print("Connected to MQTT broker! Subscribing to topics...")
            setSuccess("")
            mqtt_client.subscribe(mqtt_topic_prefix + "#")
            mqtt_client.subscribe(mqtt_topic_time)
            print("MQTT Subscriptions ready")
            requestTimesync()

        # Do non-blocking MQTT client work
        mqtt_client.loop(timeout=0.2)
        return True
    except (ValueError, RuntimeError, ConnectionError, TimeoutError,
            MQTT.MMQTTException) as e:
        print("MQTT ERROR: " + exprint(e, True))
        if type(e).__name__ == "MMQTTException":
            if str(e) == "PINGRESP not returned from broker.":
                pass
            elif str(e) == "MiniMQTT is not connected":
               pass
        elif type(e).__name__ == "ConnectionError" and str(e).startswith("Failed to send "):
            loop_n_sec(10)
            dropWifi()
        elif type(e).__name__ == "TimeoutError":
            loop_n_sec(10)
            dropWifi()
        else:
            setError("MQTT ERROR: " + exprint(e))
        return False


def requestTimesync():
    global lastTimesync
    #print("MEM: " + str(gc.mem_free()))
    try:
        mqtt_client.is_connected()  # throws if not connected
    except MQTT.MMQTTException as e:
        return

    try:
        mqtt_client.publish(mqtt_topic_time, "", retain=False, qos=0)
        lastTimesync = performance_now()
    except (ValueError, RuntimeError, ConnectionError, TimeoutError,
            MQTT.MMQTTException) as e:
        print("Time Sync Request Failed: " + exprint(e))
        setError("Time Sync Request Failed: " + exprint(e))
        loop_n_sec(10)
        dropWifi()
        return False


def dropWifi(hardResetEsp=False):
    try:
        print("WiFi D/Cing")
        setWarning("WiFi D/Cing")
        loop_n_sec(1)
        if hardResetEsp:
            print("Hard resetting ESP32 chip")
            esp.reset()  # THIS DOES NOT FIX DNS LOOKUP FAILURE
        else:
            esp.disconnect()
        print("WiFi D/Ced")
        setWarning("WiFi D/Ced")
        loop_n_sec(1)
        print("Soft Rebooting")
        setWarning("Soft Rebooting")
        loop_n_sec(1)
        supervisor.reload()
        #print("Hard Rebooting")
        #setWarning("Hard Rebooting")
        #loop_n_sec(1)
        #microcontroller.reset()
    except OSError as e:
        print("WiFi D/C FAIL: " + exprint(e))
        setError("WiFi D/C FAIL: " + exprint(e))


def clockUpdate(*, hours=None, minutes=None):
    try:
        now = time.localtime(bptime())  # Get the time values we need
    except OverflowError as e:
        now = time.localtime()

    if hours is None:
        hours = now[3]
    if (hours >= 18 and hours < 22) or (hours >= 6 and hours < 8):
        clock_label.color = 0xCC4000
    elif hours >= 18 or hours < 6:  # after 6PM or before 6AM
        clock_label.color = 0xFF0000
    else:
        clock_label.color = 0x00FF00  # daylight hours
    if hours > 12:  # Handle times later than 12:59
        hours -= 12
    elif not hours:  # Handle times between 0:00 and 0:59
        hours = 12

    if minutes is None:
        minutes = now[4]

    newText = "{hours}:{minutes:02d}".format(hours=hours, minutes=minutes)

    if clock_label.text != newText:
        clock_label.text = newText
        bbx, bby, bbwidth, bbh = clock_label.bounding_box
        clock_label.x = round(display.width / 2 - bbwidth / 2)


mqtt_topic_base = "adafruit_matrix_clock/"
mqtt_topic_prefix = mqtt_topic_base + secrets["matrix_portal_id"] + "/"
mqtt_topic_time = mqtt_topic_base + "time"

# def connected(client, userdata, flags, rc):
#    setSuccess("MQTT Connected")


def disconnected(client, userdata, rc):
    print("Disconnected from MQTT Broker!")
    setError("MQTT Disconnected")


def message(client, topic, message):
    global lastTimesync
    try:
        if topic == mqtt_topic_time:
            if message != "":
                try:
                    bptime_learn_epochms(int(message))
                    try:
                        rtc.RTC().datetime = time.localtime(bptime())
                        lastTimesync = performance_now()
                        print("MQTT Timesync Completed: " + message)
                    except OverflowError as e:
                        print("MQTT time out of range ({0})".format(message))
                        bptime_learn_epochms(time.monotonic_ns() // 1000000)
                except ValueError as e:
                    print("timestamp from MQTT was invalid (" + message + ")")
        else:
            print("MQTT > {0}: {1}".format(topic, message))
            if topic == mqtt_topic_prefix + "line1":
                setLabelFromMqtt(1, message)
            if topic == mqtt_topic_prefix + "line2":
                setLabelFromMqtt(2, message)
    except RuntimeError as e:
        print("MQTT message processing failed. {0}. Message was {2}: {3}".
              format(exprint(e, True), topic, message))


# Set up a MiniMQTT Client
pool = adafruit_connection_manager.get_radio_socketpool(esp)
ssl_context = adafruit_connection_manager.get_radio_ssl_context(esp)
mqtt_client = MQTT.MQTT(broker=secrets["mqttbroker"],
                        port=secrets["mqttport"],
                        username=secrets["mqttuser"],
                        password=secrets["mqttpass"],
                        keep_alive=12,
                        socket_pool=pool,
                        ssl_context=ssl_context,
                        socket_timeout=0.1)
# mqtt_client.on_connect = connected
mqtt_client.on_disconnect = disconnected
mqtt_client.on_message = message

while True:
    try:
        startTs = performance_now()
        clockUpdate()
        ScrollLabel(small_label1)
        ScrollLabel(small_label2)
        #crashDumpLabel.update()

        allOk = False
        if maintainWifi():
            if maintainMqtt():
                allOk = True
                if lastTimesync + 60000 < performance_now():
                    requestTimesync()
        if allOk:
            remainingMs = 200 - (performance_now() - startTs)
            if remainingMs > 10:
                time.sleep(remainingMs / 1000.0)
        else:
            loop_n_sec(1)
    except Exception as e:
        if type(e).__name__ == "KeyboardInterrupt":
            print("KeyboardInterrupt. Exiting program.")
            break
        try:
            writeErrorFile(exprint(e, True))
            #supervisor.reload()
            print("Error in outer loop: " + exprint(e, True))
            #crashDumpLabel.full_text = exprint(e, True)
            setError("LOOP ERROR: " + exprint(e, True, True))
            loop_n_sec(60)
        except Exception as e2:
            if type(e2).__name__ == "KeyboardInterrupt":
                print("KeyboardInterrupt. Exiting program.")
                break
            print("Error in outer loop error handler: " + exprint(e2, True))
            #crashDumpLabel.full_text = exprint(e2, True)
            setError("LOOP INTERNAL ERROR: " + exprint(e2, True, True))
            loop_n_sec(172800)
