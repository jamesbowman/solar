import os
import time
import serial
import json
import numpy as np
from datetime import datetime

import logging
import sensor_mqtt

def door(mag):
    door = np.array(mag)
    door_0 = np.array([-426, 926, -671])
    door_1 = np.array([-766, -1868, 492])
    d0 = np.linalg.norm(door - door_0)
    d1 = np.linalg.norm(door - door_1)
    if d0 < d1:
        return 0    # Closer to d0, so return 0
    else:
        return 1

def recv():
    port = "/dev/serial/by-id/usb-FTDI_FT232R_USB_UART_A900XSSH-if00-port0"
    port = "/dev/serial/by-id/usb-Raspberry_Pi_Picoprobe__CMSIS-DAP__E6643051575EC437-if01"
    ser = serial.Serial(port, 115200, timeout = .5)

    with sensor_mqtt.connection() as client:
        s = b''
        prev_dooropen = None
        while True:
            b = ser.read(1)
            if b:
                s += b
                if s.endswith(b'\r\n'):
                    print(s)
                    if b'{' in s and b'}' in s:
                        t0 = time.time()
                        try:
                            js = json.loads(s[s.index(b'{'):s.index(b'}') + 1])
                            js["t"] = t0
                            js["seq"]
                            js["temp"]
                            js["vbatt"]
                            js["uptime"]
                            js["dooropen"] = door(js["magnet"])
                            door_edge = (prev_dooropen, js["dooropen"])
                            print(f"{door_edge=}")
                            prev_dooropen = js["dooropen"]
                            hour = datetime.now().hour
                            if (door_edge == (1, 0)) and (hour > 15):
                                os.system("ssh pi curl --silent http://192.168.0.60/relay/0?turn=on")

                            sensor_mqtt.publish(client, "coop", js)

                        except (KeyError, UnicodeDecodeError, json.decoder.JSONDecodeError):
                            pass
                    s = b''

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    recv()
