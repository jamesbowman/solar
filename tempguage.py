"""Publish temperature each minute and display LiTime charging power in watts.

Run: python tempguage.py /dev/tty.usbserial-DK0F79X0
The left DIG2 (0x14) shows rounded temperature in degrees Celsius.
The right DIG2s (0x15, 0x16) show watts with leading zeros suppressed.
Power brightness fades from 255 to 50 over the first 20 seconds of data age.
Missing, invalid, disconnected, or >60-second-old power readings blank watts.
"""

import sys
import struct
import time
import json
import math
import queue
import i2cdriver, EDS

import logging
import sensor_mqtt

LOG = logging.getLogger(__name__)
DISPLAY_ADDRESSES = (0x14, 0x15, 0x16)
STALE_SECONDS = 60
FADE_SECONDS = 20
MIN_POWER_BRIGHTNESS = 50
# Bits 0–6 are A–G; bit 7 is the decimal point, as in eds-7seg/main.fs.
GLYPHS = (0x3F, 0x06, 0x5B, 0x4F, 0x66, 0x6D, 0x7D, 0x07, 0x7F, 0x6F)


def digit_patterns(number, width):
    if number is None:
        return (0,) * width
    text = str(number).rjust(width)
    if len(text) > width:
        raise ValueError("number does not fit display")
    return tuple(0 if char == ' ' else 0x40 if char == '-' else GLYPHS[int(char)]
                 for char in text)


def nonnegative_number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("expected a number")
    if not math.isfinite(value) or value < 0:
        raise ValueError("expected a finite, nonnegative number")
    return value


def solar_power(sample):
    """Charging-side solar power in watts; panel voltage is not battery voltage."""
    if 'battery_power_w' in sample:
        watts = nonnegative_number(sample['battery_power_w'])
    else:
        watts = (nonnegative_number(sample['battery_voltage_v']) *
                 nonnegative_number(sample['battery_current_a']))
    if not math.isfinite(watts):
        raise ValueError("power is not finite")
    watts = int(watts + 0.5)
    if watts > 9999:
        raise ValueError("power is outside the four-digit display range")
    return watts


class SolarReadings:
    """Only the latest reading crosses from the MQTT thread to the I²C thread."""

    def __init__(self):
        self.updates = queue.Queue(maxsize=1)

    def on_message(self, client, userdata, message):
        if message.topic != 'litime':
            return
        update = None
        try:
            sample = json.loads(message.payload)
            if not isinstance(sample, dict):
                raise ValueError("expected a JSON object")
            timestamp = nonnegative_number(sample['t'])
            age = time.time() - timestamp
            if not -5 <= age < STALE_SECONDS:
                raise ValueError("reading is stale or has a future timestamp")
            update = (solar_power(sample), time.monotonic() + STALE_SECONDS - max(0, age))
        except (ValueError, KeyError, TypeError, OverflowError) as exc:
            LOG.warning("Ignoring invalid LiTime reading: %s", exc)
        # Invalid readings blank the display instead of implying a zero measurement.
        try:
            self.updates.get_nowait()
        except queue.Empty:
            pass
        self.updates.put_nowait(update)


class PowerDisplay:
    """Raw DIG2 segments: temperature on the left, four power digits on the right.

    Protocol: https://electricdollarstore.com/dig2.html
    """

    def __init__(self, i2):
        self.modules = [EDS.Dig2(i2, address) for address in DISPLAY_ADDRESSES]
        self.shown = None
        self.temperature_shown = None
        self.power_brightness = 255
        for module in self.modules:
            module.raw(0, 0)
            module.dp(0, 0)
            module.brightness(255)

    def set_power_age(self, age):
        fraction = min(1, max(0, age / FADE_SECONDS))
        brightness = int(255 - (255 - MIN_POWER_BRIGHTNESS) * fraction + 0.5)
        if brightness != self.power_brightness:
            for module in self.modules[1:]:
                module.brightness(brightness)
            self.power_brightness = brightness

    def show(self, watts):
        if watts == self.shown:
            return
        patterns = digit_patterns(watts, 4)
        # raw(dig0, dig1): left digit first, then right digit on each module.
        for module, offset in zip(self.modules[1:], (0, 2)):
            module.raw(*patterns[offset:offset + 2])
        if watts is None:
            LOG.info("Solar display blank (no fresh MQTT reading)")
        else:
            LOG.info("Solar display: %4d W", watts)
        self.shown = watts

    def show_temperature(self, temperature):
        degrees = None
        if temperature is not None:
            try:
                if isinstance(temperature, bool) or not math.isfinite(temperature):
                    raise ValueError("temperature is not finite")
                # Round halves away from zero; a minus sign occupies one digit.
                degrees = (math.floor(temperature + 0.5) if temperature >= 0
                           else math.ceil(temperature - 0.5))
                if not -9 <= degrees <= 99:
                    raise ValueError("temperature is outside the two-digit display range")
            except (TypeError, ValueError, OverflowError) as exc:
                LOG.warning("Temperature display blank: %s", exc)
                degrees = None
        if degrees != self.temperature_shown:
            self.modules[0].raw(*digit_patterns(degrees, 2))
            LOG.info("Temperature display: %s", "blank" if degrees is None else "%d C" % degrees)
            self.temperature_shown = degrees

def tempgauge():
    i2=i2cdriver.I2CDriver(sys.argv[1])
    display = None
    try:
        i2.scan()
        display = PowerDisplay(i2)
        d = EDS.Temp(i2)
        readings = SolarReadings()
        with sensor_mqtt.connection(subscriptions=('litime',), on_message=readings.on_message) as client:
            next_temperature = time.time()
            latest = None
            while True:
                # Keep all I²C transactions on this thread. Waiting for MQTT does
                # not delay display refresh until the next temperature sample.
                try:
                    latest = readings.updates.get(timeout=0.1)
                except queue.Empty:
                    pass
                if not client.is_connected():
                    latest = None
                monotonic_now = time.monotonic()
                if latest is not None and monotonic_now >= latest[1]:
                    latest = None
                if latest is not None:
                    # Expiry already accounts for the source timestamp's age.
                    # Refresh brightness even when the watt value is unchanged.
                    display.set_power_age(STALE_SECONDS - (latest[1] - monotonic_now))
                display.show(latest[0] if latest is not None else None)

                now = time.time()
                if now >= next_temperature:
                    next_temperature = (math.floor(now / 60) + 1) * 60
                    try:
                        sample = {'t': now, 'temp': d.read()}
                    except struct.error as exc:
                        LOG.warning("Temperature read failed: %s", exc)
                        display.show_temperature(None)
                    else:
                        display.show_temperature(sample['temp'])
                        sensor_mqtt.publish(client, "sungauge40", sample)
    finally:
        try:
            if display is not None:
                display.show(None)
                display.show_temperature(None)
        finally:
            i2.ser.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        tempgauge()
    except KeyboardInterrupt:
        pass
