"""
Wokwi node for Helix Residences communal environmental monitoring.

This ESP32 script models one embedded sensing node that could be placed in a
communal zone such as the gym or co-working suite. It reads:

- DHT22 for temperature and humidity
- potentiometer as a gas / CO2-VOC proxy input
- photoresistor for light level
- slide switch for window or vent position

It then classifies the state as Safe, Warning, or Danger and drives:

- green LED for Safe
- amber LED for Warning
- red LED and buzzer for Danger

The serial output is designed to align conceptually with the Python dashboard,
which acts as the monitoring and analytics layer.
"""

from machine import ADC, Pin, PWM
import dht
import json
import time


TEMP_SAFE_MIN = 19.0
TEMP_SAFE_MAX = 24.0
TEMP_WARNING_MIN = 17.0
TEMP_WARNING_MAX = 27.0

HUMIDITY_SAFE_MIN = 35.0
HUMIDITY_SAFE_MAX = 60.0
HUMIDITY_WARNING_MIN = 30.0
HUMIDITY_WARNING_MAX = 70.0

AIR_SAFE_MAX = 800
AIR_WARNING_MAX = 1200

LIGHT_SAFE_MIN = 250
LIGHT_WARNING_MIN = 150


sensor_dht = dht.DHT22(Pin(15))
air_quality_pot = ADC(Pin(34))
air_quality_pot.atten(ADC.ATTN_11DB)
light_sensor = ADC(Pin(35))
light_sensor.atten(ADC.ATTN_11DB)
vent_switch = Pin(27, Pin.IN, Pin.PULL_UP)

green_led = Pin(18, Pin.OUT)
amber_led = Pin(19, Pin.OUT)
red_led = Pin(21, Pin.OUT)
buzzer = PWM(Pin(22))
buzzer.duty(0)


def range_status(value, safe_min, safe_max, warning_min, warning_max):
    if safe_min <= value <= safe_max:
        return "Safe"
    if warning_min <= value <= warning_max:
        return "Warning"
    return "Danger"


def max_only_status(value, safe_max, warning_max):
    if value <= safe_max:
        return "Safe"
    if value <= warning_max:
        return "Warning"
    return "Danger"


def min_only_status(value, safe_min, warning_min):
    if value >= safe_min:
        return "Safe"
    if value >= warning_min:
        return "Warning"
    return "Danger"


def convert_air_quality(raw_value):
    return int(450 + (raw_value / 4095) * 1250)


def convert_light(raw_value):
    return int(80 + (raw_value / 4095) * 720)


def vent_state():
    return "Open" if vent_switch.value() == 0 else "Closed"


def overall_status(statuses):
    if "Danger" in statuses:
        return "Danger"
    if "Warning" in statuses:
        return "Warning"
    return "Safe"


def recommendation(status, air_quality, current_vent_state):
    if status == "Danger" and air_quality > AIR_WARNING_MAX:
        return "Investigate poor indoor air quality and increase ventilation immediately."
    if status == "Warning" and current_vent_state == "Closed":
        return "Open ventilation and continue monitoring conditions."
    if status == "Warning":
        return "Review the zone for developing comfort issues."
    return "No immediate action required."


def update_indicators(status):
    green_led.value(1 if status == "Safe" else 0)
    amber_led.value(1 if status == "Warning" else 0)
    red_led.value(1 if status == "Danger" else 0)

    if status == "Danger":
        buzzer.freq(1200)
        buzzer.duty(512)
    else:
        buzzer.duty(0)


while True:
    sensor_dht.measure()
    temperature = round(sensor_dht.temperature(), 1)
    humidity = round(sensor_dht.humidity(), 1)
    air_quality = convert_air_quality(air_quality_pot.read())
    light_level = convert_light(light_sensor.read())
    current_vent_state = vent_state()

    statuses = {
        "temperature": range_status(
            temperature,
            TEMP_SAFE_MIN,
            TEMP_SAFE_MAX,
            TEMP_WARNING_MIN,
            TEMP_WARNING_MAX,
        ),
        "humidity": range_status(
            humidity,
            HUMIDITY_SAFE_MIN,
            HUMIDITY_SAFE_MAX,
            HUMIDITY_WARNING_MIN,
            HUMIDITY_WARNING_MAX,
        ),
        "air_quality": max_only_status(air_quality, AIR_SAFE_MAX, AIR_WARNING_MAX),
        "light_level": min_only_status(light_level, LIGHT_SAFE_MIN, LIGHT_WARNING_MIN),
    }

    status = overall_status(list(statuses.values()))
    update_indicators(status)

    payload = {
        "zone": "Embedded communal node",
        "temperature_c": temperature,
        "humidity_pct": humidity,
        "air_quality_proxy_ppm": air_quality,
        "light_level_proxy": light_level,
        "vent_state": current_vent_state,
        "status": status,
        "metric_states": statuses,
        "recommendation": recommendation(status, air_quality, current_vent_state),
    }
    print(json.dumps(payload))
    time.sleep(2)
