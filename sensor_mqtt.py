"""MQTT connection shared by the coop and temperature sensor services."""

from contextlib import contextmanager
import json
import logging

import paho.mqtt.client as mqtt

LOG = logging.getLogger(__name__)


def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code.is_failure:
        LOG.warning("MQTT connection rejected: %s", reason_code)
    else:
        LOG.info("MQTT connected")


def on_disconnect(client, userdata, flags, reason_code, properties):
    if reason_code.is_failure:
        LOG.warning("MQTT disconnected: %s; reconnecting", reason_code)


def on_connect_fail(client, userdata):
    LOG.warning("MQTT connection attempt failed; retrying")


@contextmanager
def connection(host="pi", port=1883, subscriptions=(), on_message=None):
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

    def connected(client, userdata, flags, reason_code, properties):
        on_connect(client, userdata, flags, reason_code, properties)
        if not reason_code.is_failure and subscriptions:
            result, _ = client.subscribe([(topic, 0) for topic in subscriptions])
            if result != mqtt.MQTT_ERR_SUCCESS:
                LOG.warning("MQTT subscription failed: %s", mqtt.error_string(result))

    # Install callbacks before connecting, and resubscribe after every reconnect.
    client.on_connect = connected
    client.on_message = on_message
    client.on_disconnect = on_disconnect
    client.on_connect_fail = on_connect_fail
    client.reconnect_delay_set(min_delay=1, max_delay=30)
    # The background loop retries even if the broker is down at startup.
    client.connect_async(host, port, keepalive=60)
    client.loop_start()
    try:
        yield client
    finally:
        client.disconnect()
        client.loop_stop()


def publish(client, topic, sample):
    # Live telemetry: do not accumulate old measurements during an outage.
    if not client.is_connected():
        LOG.warning("MQTT unavailable; skipping %s sample", topic)
        return False
    result = client.publish(topic, json.dumps(sample), qos=0, retain=False)
    if result.rc != mqtt.MQTT_ERR_SUCCESS:
        LOG.warning("MQTT publish to %s failed: %s", topic, mqtt.error_string(result.rc))
        return False
    return True
