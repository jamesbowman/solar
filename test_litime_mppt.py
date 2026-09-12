import struct
import unittest

from litime_mppt import FrameDecoder, REQUEST, crc16, decode_sample

# Captured from BT-LTMPPT2430 on cam1, 2026-09-12.
CAPTURE = bytes.fromhex(
    "010326006400860a8901692aff00000000000002cb016e017d000000020000"
    "00000000017d00000000c1f7"
)


def with_crc(data):
    return data + struct.pack("<H", crc16(data))


class ProtocolTests(unittest.TestCase):
    def test_real_controller_sample(self):
        sample = decode_sample(CAPTURE)
        self.assertEqual(sample["battery_voltage_v"], 13.4)
        self.assertEqual(sample["battery_current_a"], 26.97)
        self.assertEqual(sample["battery_power_w"], 361)
        self.assertEqual(sample["controller_temperature_c"], 42)
        self.assertEqual(sample["panel_voltage_v"], 71.5)
        self.assertEqual(sample["energy_today_wh"], 381)
        self.assertEqual(sample["total_energy_wh"], 381)
        self.assertEqual(len(sample["registers"]), 19)

    def test_read_request_crc(self):
        self.assertEqual(crc16(REQUEST), 0)
        self.assertEqual(REQUEST[:6], bytes.fromhex("010301010013"))

    def test_all_fragment_boundaries(self):
        for split in range(1, len(CAPTURE)):
            decoder = FrameDecoder()
            self.assertEqual(decoder.feed(CAPTURE[:split]), [])
            self.assertEqual(decoder.feed(CAPTURE[split:]), [CAPTURE])

    def test_noise_and_concatenated_frames(self):
        self.assertEqual(FrameDecoder().feed(b"noise" + CAPTURE * 2), [CAPTURE, CAPTURE])

    def test_corrupt_frame_followed_by_valid_frame(self):
        corrupt = bytearray(CAPTURE)
        corrupt[7] ^= 1
        self.assertEqual(FrameDecoder().feed(corrupt + CAPTURE), [CAPTURE])
        with self.assertRaises(ValueError):
            decode_sample(corrupt)

    def test_modbus_exception(self):
        error = with_crc(bytes.fromhex("018302"))
        self.assertEqual(FrameDecoder().feed(error), [error])

    def test_total_energy_uses_unsigned_32_bits(self):
        data = bytearray(CAPTURE[:-2])
        data[33:37] = bytes.fromhex("fedcba98")
        self.assertEqual(decode_sample(with_crc(data))["total_energy_wh"], 0xFEDCBA98)

    def test_unknown_status_preserved(self):
        data = bytearray(CAPTURE[:-2])
        data[27:29] = bytes.fromhex("1234")
        sample = decode_sample(with_crc(data))
        self.assertEqual(sample["load_status"], "unknown")
        self.assertEqual(sample["load_status_raw"], 0x1234)


if __name__ == "__main__":
    unittest.main()
