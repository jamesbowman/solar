#!/usr/bin/env python3
"""Read LiTime MPPT telemetry over BLE; emit JSON lines and optionally MQTT.

Register layout references and unresolved fields are documented in LITIME.md.
Only the Modbus function 03 telemetry request is sent to the controller.
"""

import argparse
import asyncio
import json
import logging
import math
import signal
import struct
import time

LOG = logging.getLogger("litime")
ADDRESS = "C8:47:80:63:1B:C3"
CHARACTERISTIC = "0000ffe1-0000-1000-8000-00805f9b34fb"
REQUEST = bytes.fromhex("010301010013543b")


def crc16(data):
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ (0xA001 if crc & 1 else 0)
    return crc


class FrameDecoder:
    """Reassemble fragmented notifications and reject corrupt Modbus frames."""

    def __init__(self):
        self.buffer = bytearray()

    def feed(self, data):
        self.buffer.extend(data)
        frames = []
        while len(self.buffer) >= 3:
            if self.buffer[:3] == b"\x01\x03\x26":
                size = 43
            elif self.buffer[:2] == b"\x01\x83":
                size = 5
            else:
                del self.buffer[0]
                continue
            if len(self.buffer) < size:
                break
            frame = bytes(self.buffer[:size])
            if crc16(frame):
                LOG.warning("Discarding frame with invalid CRC: %s", frame.hex())
                del self.buffer[0]
                continue
            del self.buffer[:size]
            frames.append(frame)
        return frames


def decode_sample(frame):
    if len(frame) != 43 or frame[:3] != b"\x01\x03\x26" or crc16(frame):
        raise ValueError("Invalid telemetry frame")
    r = struct.unpack(">19H", frame[3:-2])
    return {
        "battery_voltage_v": r[1] / 10,
        "battery_current_a": r[2] / 100,
        "battery_power_w": r[3],
        "controller_temperature_c": r[4] >> 8,
        "load_voltage_v": r[5] / 10,
        "load_current_a": r[6] / 100,
        # Published decoders disagree about the load power scale; keep it raw.
        "load_power_raw": r[7],
        "panel_voltage_v": r[8] / 10,
        "max_charge_power_today_w": r[9],
        "energy_today_wh": r[10],
        "load_status": {2: "on", 32770: "off"}.get(r[12], "unknown"),
        "load_status_raw": r[12],
        "running_days": r[14],
        "total_energy_wh": (r[15] << 16) | r[16],
        "registers": {f"0x{0x101 + i:04x}": value for i, value in enumerate(r)},
        "raw_frame": frame.hex(),
    }


class MqttSink:
    """Best-effort live telemetry; broker outages never stop stdout logging."""

    def __init__(self, host, port, topic):
        import paho.mqtt.client as mqtt

        self.topic = topic
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.reconnect_delay_set(min_delay=1, max_delay=30)
        self.client.connect_async(host, port, keepalive=60)
        self.client.loop_start()

    def on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code.is_failure:
            LOG.warning("MQTT connection rejected: %s", reason_code)
        else:
            LOG.info("MQTT connected; publishing to %s", self.topic)

    def on_disconnect(self, client, userdata, flags, reason_code, properties):
        if reason_code.is_failure:
            LOG.warning("MQTT disconnected: %s; reconnecting", reason_code)

    def publish(self, payload):
        if not self.client.is_connected():
            LOG.warning("MQTT unavailable; sample written to stdout only")
            return
        # Live samples only: no retained values or stale backlog after an outage.
        result = self.client.publish(self.topic, payload, qos=0, retain=False)
        if result.rc:
            LOG.warning("MQTT publish failed: %s", result.rc)

    def close(self):
        self.client.disconnect()
        self.client.loop_stop()


async def read_connection(args, sink, remaining):
    from bleak import BleakClient, BleakScanner

    LOG.info("Looking for %s", args.address)
    device = await BleakScanner.find_device_by_address(args.address, timeout=args.timeout)
    if device is None:
        raise TimeoutError("Controller not advertising; check for an active phone connection")
    decoder = FrameDecoder()
    responses = asyncio.Queue(maxsize=4)

    def notify(_, data):
        LOG.debug("BLE RX %s", data.hex())
        for frame in decoder.feed(data):
            if responses.full():
                responses.get_nowait()
            responses.put_nowait(frame)

    async with BleakClient(device, timeout=args.timeout) as client:
        characteristic = client.services.get_characteristic(CHARACTERISTIC)
        if characteristic is None:
            raise RuntimeError("Controller telemetry characteristic is missing")
        await client.start_notify(characteristic, notify)
        LOG.info("Connected to %s (%s)", device.name, device.address)
        while True:
            if not client.is_connected:
                raise ConnectionError("Bluetooth disconnected")
            decoder.buffer.clear()
            while not responses.empty():
                responses.get_nowait()
            async with asyncio.timeout(args.timeout):
                await client.write_gatt_char(
                    characteristic, REQUEST, response="write" in characteristic.properties
                )
                frame = await responses.get()
            if frame[1] == 0x83:
                raise RuntimeError(f"Controller returned Modbus exception {frame[2]}")
            sample = {
                "t": time.time(),
                "device": device.name,
                "address": device.address,
                **decode_sample(frame),
            }
            payload = json.dumps(sample, separators=(",", ":"), allow_nan=False)
            print(payload, flush=True)
            if sink:
                sink.publish(payload)
            if remaining is not None:
                remaining[0] -= 1
                if remaining[0] == 0:
                    return
            await asyncio.sleep(args.interval)


async def run(args):
    sink = MqttSink(args.mqtt_host, args.mqtt_port, args.mqtt_topic) if args.mqtt_host else None
    remaining = [args.samples] if args.samples else None
    task = asyncio.current_task()
    for sig in (signal.SIGTERM, signal.SIGINT):
        asyncio.get_running_loop().add_signal_handler(sig, task.cancel)
    try:
        while True:
            try:
                await read_connection(args, sink, remaining)
                return
            except (OSError, RuntimeError, TimeoutError) as exc:
                # BleakError is handled below without requiring bleak for parser tests.
                if args.samples:
                    raise
                LOG.warning("Read failed (%s: %s); retrying in %ss", type(exc).__name__, exc, args.retry)
            except Exception as exc:
                from bleak.exc import BleakError
                if args.samples or not isinstance(exc, BleakError):
                    raise
                LOG.warning("Bluetooth error: %s; retrying in %ss", exc, args.retry)
            await asyncio.sleep(args.retry)
    finally:
        if sink:
            sink.close()


def positive_seconds(value):
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError("must be a finite positive number")
    return number


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--address", default=ADDRESS)
    parser.add_argument("--interval", type=positive_seconds, default=10)
    parser.add_argument("--timeout", type=positive_seconds, default=20)
    parser.add_argument("--retry", type=positive_seconds, default=10)
    parser.add_argument("--samples", type=int, default=0, help="exit after N samples; 0 runs forever")
    parser.add_argument("--mqtt-host", help="enable MQTT, e.g. pi; stdout is always enabled")
    parser.add_argument("--mqtt-port", type=int, default=1883)
    parser.add_argument("--mqtt-topic", default="litime")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    if args.samples < 0:
        parser.error("--samples must be nonnegative")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if args.debug:
        LOG.setLevel(logging.DEBUG)
    try:
        asyncio.run(run(args))
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass


if __name__ == "__main__":
    main()
