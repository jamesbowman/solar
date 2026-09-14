import json
import time
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from tempguage import PowerDisplay, SolarReadings, solar_power


class DisplayTests(unittest.TestCase):
    def test_power_uses_reported_watts_or_battery_voltage_times_current(self):
        self.assertEqual(solar_power({'battery_power_w': 411}), 411)
        self.assertEqual(solar_power({'battery_voltage_v': 13.6, 'battery_current_a': 30,
                                     'panel_voltage_v': 70}), 408)
        self.assertEqual(solar_power({'battery_power_w': 0}), 0)
        self.assertEqual(solar_power({'battery_power_w': 400.6}), 401)

    def test_invalid_power_is_not_displayed_as_zero_or_wrapped(self):
        for value in (None, True, '400', -1, float('nan'), float('inf'), 10000, 9999.5):
            with self.subTest(value=value), self.assertRaises(ValueError):
                solar_power({'battery_power_w': value})

    def test_four_power_digits_with_leading_zero_suppression(self):
        bus = Mock()
        display = PowerDisplay(bus)
        for watts, left, right in ((1234, b'\x06\x5b', b'\x4f\x66'),
                                   (411, b'\x00\x66', b'\x06\x06'),
                                   (12, b'\x00\x00', b'\x06\x5b'),
                                   (0, b'\x00\x00', b'\x00\x3f')):
            bus.reset_mock()
            display.show(watts)
            self.assertEqual(bus.regwr.call_args_list, [
                unittest.mock.call(0x15, 0, left),
                unittest.mock.call(0x16, 0, right),
            ])
            bus.reset_mock()
            display.show(watts)
            bus.regwr.assert_not_called()
        bus.reset_mock()
        display.show(None)
        self.assertEqual(bus.regwr.call_args_list, [
            unittest.mock.call(address, 0, b'\0\0') for address in (0x15, 0x16)
        ])

    def test_temperature_rounding_sign_and_blanking_only_left_module(self):
        bus = Mock()
        display = PowerDisplay(bus)
        for temperature, raw in ((22.5, b'\x5b\x4f'), (7.4, b'\x00\x07'),
                                 (-2.5, b'\x40\x4f'), (0, b'\x00\x3f'),
                                 (100, b'\x00\x00'), (21.6, b'\x5b\x5b'),
                                 (None, b'\x00\x00')):
            bus.reset_mock()
            display.show_temperature(temperature)
            bus.regwr.assert_called_once_with(0x14, 0, raw)

    def test_power_fades_and_recovers_without_changing_digits_or_temperature(self):
        bus = Mock()
        display = PowerDisplay(bus)
        display.show(411)
        for age, brightness in ((5, 204), (10, 153), (20, 50), (0, 255)):
            bus.reset_mock()
            display.set_power_age(age)
            display.show(411)
            self.assertEqual(bus.regwr.call_args_list, [
                unittest.mock.call(address, 4, brightness) for address in (0x15, 0x16)
            ])
            bus.reset_mock()
            display.set_power_age(age)
            bus.regwr.assert_not_called()
        bus.reset_mock()
        display.set_power_age(-1)
        bus.regwr.assert_not_called()
        display.set_power_age(20)
        bus.reset_mock()
        display.set_power_age(59)
        bus.regwr.assert_not_called()

    def test_delayed_reading_preserves_its_age_for_fading(self):
        readings = SolarReadings()
        message = SimpleNamespace(topic='litime', payload=json.dumps({
            't': 990, 'battery_power_w': 411,
        }))
        with patch('tempguage.time.time', return_value=1000), \
             patch('tempguage.time.monotonic', return_value=500):
            readings.on_message(None, None, message)
        watts, expiry = readings.updates.get_nowait()
        self.assertEqual((watts, expiry), (411, 550))

    def test_callback_keeps_latest_and_rejects_stale_or_invalid_messages(self):
        readings = SolarReadings()
        def deliver(sample):
            readings.on_message(None, None, SimpleNamespace(topic='litime', payload=json.dumps(sample)))
        deliver({'t': time.time(), 'battery_power_w': 400})
        deliver({'t': time.time(), 'battery_power_w': 411})
        watts, expiry = readings.updates.get_nowait()
        self.assertEqual(watts, 411)
        self.assertGreater(expiry, time.monotonic() + 55)
        for sample in ({'t': time.time()-120, 'battery_power_w': 400},
                       {'battery_power_w': 400}, {'t': time.time()+120, 'battery_power_w': 400}, []):
            deliver(sample)
            self.assertIsNone(readings.updates.get_nowait())


if __name__ == '__main__':
    unittest.main()
