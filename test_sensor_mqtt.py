"""Integration test: run with paho-mqtt 2.x and a local mosquitto executable."""

from contextlib import ExitStack
import json
from pathlib import Path
import queue
import shutil
import socket
import subprocess
import tempfile
import threading
import time
import unittest

import sensor_mqtt


@unittest.skipUnless(shutil.which("mosquitto"), "mosquitto is required")
class BrokerRecoveryTest(unittest.TestCase):
    def setUp(self):
        self.broker = None
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.addCleanup(self.stop_broker)
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            self.port = sock.getsockname()[1]
        self.config = Path(self.directory.name) / "mosquitto.conf"
        self.config.write_text(
            "listener {} 127.0.0.1\nallow_anonymous true\npersistence false\n".format(self.port)
        )

    def wait_for(self, predicate, message):
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if predicate():
                return
            time.sleep(0.05)
        self.fail(message)

    def start_broker(self):
        self.broker = subprocess.Popen(
            [shutil.which("mosquitto"), "-c", str(self.config)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        def listening():
            if self.broker.poll() is not None:
                self.fail("Test broker exited before opening its listener")
            try:
                with socket.create_connection(("127.0.0.1", self.port), timeout=0.1):
                    return True
            except OSError:
                return False
        self.wait_for(listening, "Test broker did not start")

    def stop_broker(self):
        if self.broker is not None:
            self.broker.terminate()
            self.broker.wait(timeout=5)
            self.broker = None

    def test_initial_outage_and_broker_restart_for_both_publishers(self):
        received = queue.Queue()
        subscribed = threading.Event()
        attempted = threading.Event()
        topics = ("coop", "sungauge40")
        with ExitStack() as stack:
            publishers = [stack.enter_context(sensor_mqtt.connection("127.0.0.1", self.port))
                          for _ in topics]
            for client in publishers:
                client.on_connect_fail = lambda c, u: attempted.set()
            self.assertTrue(attempted.wait(10), "No connection attempt while broker was down")
            for client, topic in zip(publishers, topics):
                self.assertFalse(sensor_mqtt.publish(client, topic, {"phase": "offline"}))

            self.start_broker()
            self.wait_for(lambda: all(c.is_connected() for c in publishers), "Initial connection failed")

            subscriber = sensor_mqtt.mqtt.Client(sensor_mqtt.mqtt.CallbackAPIVersion.VERSION2)
            subscriber.on_connect = lambda c, u, f, rc, p: c.subscribe([(t, 0) for t in topics])
            subscriber.on_subscribe = lambda *args: subscribed.set()
            subscriber.on_message = lambda c, u, m: received.put((m.topic, json.loads(m.payload)))
            subscriber.reconnect_delay_set(1, 2)
            subscriber.connect_async("127.0.0.1", self.port)
            subscriber.loop_start()
            stack.callback(subscriber.loop_stop)
            stack.callback(subscriber.disconnect)
            self.assertTrue(subscribed.wait(10), "Subscriber did not connect")

            def check_delivery(phase):
                for client, topic in zip(publishers, topics):
                    self.assertTrue(sensor_mqtt.publish(client, topic, {"phase": phase}))
                messages = [received.get(timeout=10) for _ in topics]
                self.assertEqual(dict(messages), {t: {"phase": phase} for t in topics})

            check_delivery("before restart")
            self.stop_broker()
            self.wait_for(lambda: all(not c.is_connected() for c in publishers), "Disconnect not detected")
            subscribed.clear()
            for client, topic in zip(publishers, topics):
                self.assertFalse(sensor_mqtt.publish(client, topic, {"phase": "offline"}))
            self.start_broker()
            self.wait_for(lambda: all(c.is_connected() for c in publishers), "Automatic reconnect failed")
            self.assertTrue(subscribed.wait(10), "Subscriber did not reconnect")
            check_delivery("after restart")

    def test_subscription_is_restored_after_broker_restart(self):
        self.start_broker()
        received = queue.Queue()
        def on_message(client, userdata, message):
            received.put(json.loads(message.payload))
        with sensor_mqtt.connection("127.0.0.1", self.port) as publisher:
            with sensor_mqtt.connection("127.0.0.1", self.port, subscriptions=('litime',),
                                        on_message=on_message) as subscriber:
                def check_delivery(phase):
                    self.wait_for(lambda: publisher.is_connected() and subscriber.is_connected(),
                                  "Clients did not connect")
                    deadline = time.monotonic() + 10
                    while time.monotonic() < deadline:
                        sensor_mqtt.publish(publisher, 'litime', {'phase': phase})
                        try:
                            if received.get(timeout=0.2) == {'phase': phase}:
                                return
                        except queue.Empty:
                            pass
                    self.fail("Subscription did not receive " + phase)
                check_delivery('before restart')
                self.stop_broker()
                self.wait_for(lambda: not publisher.is_connected() and not subscriber.is_connected(),
                              "Disconnect not detected")
                self.start_broker()
                check_delivery('after restart')


if __name__ == "__main__":
    unittest.main()
