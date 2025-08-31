import paho.mqtt.client as mqtt

# Callback when connection is established
def on_connect(client, userdata, flags, rc):
    print("Connected with result code", rc)
    # Subscribe to everything
    client.subscribe("#")

# Callback when a message is received
def on_message(client, userdata, msg):
    print(f"[{msg.topic}] {msg.payload.decode(errors='replace')}")

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

# Replace with your broker address/port
client.connect("pi", 1883, 60)

client.loop_forever()
