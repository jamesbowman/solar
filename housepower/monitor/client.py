import sys
import math
import numpy as np
import paho.mqtt.client as mqtt
import matplotlib.pyplot as plt

def on_connect(client, userdata, flags, rc):
    client.subscribe("houseac/status")
    client.subscribe("houseac/power")

def on_message(client, userdata, msg):
    # print(f"{msg.topic=}, {samples=}")

    if msg.topic == 'houseac/status':
        print("---> status", msg.payload.decode())
    elif msg.topic == 'houseac/power':
        de = msg.payload.decode()
        print(de)
        return

        samples = np.frombuffer(bytes.fromhex(de), np.uint8).astype(float)

        rms = math.sqrt(np.mean((samples - 127.5) ** 2))
        p = rms * 1300 / 42
        print(f"{p=}")

        if 0:
            plt.plot(samples)
            plt.show()
            sys.exit(0)

client = mqtt.Client()
client.connect("pi", 1883, 60)

client.on_connect = on_connect
client.on_message = on_message

client.loop_forever()
