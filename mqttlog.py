import sys
import os
import time
from pathlib import Path
import json

import paho.mqtt.client as mqtt

def on_connect(client, userdata, flags, rc):
    client.subscribe("#")

def log(dir, dd):
    t = time.time()
    path = Path.home() / "tsd" / dir
    os.makedirs(path, exist_ok=True)
    dd['t'] = t
    with open(path / f"{t}.json", "wt") as f:
        json.dump(dd, f)

def jlog(dir, msg):
    c = json.loads(msg)
    if 't' in c:
        t = c['t']
    else:
        t = time.time()
    path = Path.home() / "tsd" / dir
    os.makedirs(path, exist_ok=True)
    with open(path / f"{t}.json", "wt") as f:
        f.write(msg)

def on_message(client, userdata, msg):
    print(f"{msg.topic=} {msg.payload.decode()}")

    t = time.time()
    de = msg.payload.decode()

    if msg.topic == 'houseac/power':
        log("houseac", {'power' : float(de)})
    jsons = (
        'bedroom',
        'shellyplugus-d4d4da092de4/status/switch:0',
        'coop',
        'renogy',
        'sungauge40',
    )
    if msg.topic in jsons:
        jlog(msg.topic, de)

client = mqtt.Client()

client.on_connect = on_connect
client.on_message = on_message

client.connect("pi", 1883, 60)

client.loop_forever()
