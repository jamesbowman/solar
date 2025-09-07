import time
import array
import math
import microcontroller
import watchdog
import gc

microcontroller.watchdog.timeout = 8
microcontroller.watchdog.mode = watchdog.WatchDogMode.RESET
microcontroller.watchdog.feed()  # kick it once at start

import ulab.numpy as np
import board
from analogio import AnalogIn
import analogbufio

import os
import wifi
import socketpool
# import ssl
import adafruit_minimqtt.adafruit_minimqtt as MQTT
import adafruit_ntp

rate = 4800
length = 60 * rate // 60
mybuffer = bytearray(length)
adcbuf = analogbufio.BufferedIn(board.GP26, sample_rate=rate)

class App:

    def __init__(self):
        ssid = os.getenv('CIRCUITPY_WIFI_SSID')
        pw = os.getenv('CIRCUITPY_WIFI_PASSWORD')
        print("Connecting to WiFi", ssid, pw)

        #  connect to your SSID
        wifi.radio.connect(ssid, pw)

        print("Connected to WiFi")

        pool = socketpool.SocketPool(wifi.radio)

        print("My MAC addr:", wifi.radio.mac_address.hex(':'))
        print("My IP address is", wifi.radio.ipv4_address)

        def connected(client, userdata, flags, rc):
            self.is_connected = True

        self.is_connected = False
        mqtt_client = MQTT.MQTT(
            broker="192.168.1.20",
            port=1883,
            socket_pool=pool,
            is_ssl=False
            # ssl_context=ssl.create_default_context()
        )

        mqtt_client.on_connect = connected

        print("Connecting...")
        mqtt_client.connect()
        while not self.is_connected:
            time.sleep(1)
        assert self.is_connected
        print("Connected to MQTT broker!")


        mqtt_client.publish("houseac/status", 'reset')
        while True:
            gc.collect()
            # ww = [buf_analog() * 2336 for i in range(cycle)]
            # w = int(sum(ww)) // cycle
            sa = self.sample()

            ua = np.frombuffer(sa, dtype=np.uint8)
            rms = math.sqrt(np.mean((ua - 127.5) ** 2))
            p = rms * 670 / 22.15
            print(f"{len(sa)} samples, {rms=} {p=}")

            # mqtt_client.publish("houseac/raw", sa.hex())
            mqtt_client.publish("houseac/power", str(p))
            microcontroller.watchdog.feed()

    def sample(self):
        adcbuf.readinto(mybuffer)
        return mybuffer

App()
