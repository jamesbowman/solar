import time
import json
from renogy_rover import RenogyRover

if __name__ == "__main__":
    portname="/dev/serial/by-id/usb-FTDI_FT232R_USB_UART_A9GIWNYB-if00-port0"
    rover = RenogyRover(portname, 1)
    print([
        int(time.time()),
        rover.battery_percentage(),
        rover.battery_voltage(),
        round(rover.solar_voltage() * rover.solar_current(), 2)
    ])
    with open('instantaneous.json', 'w') as f:
        json.dump([
            ('Battery %',                             rover.battery_percentage(),          '%'),
            ('Battery Type',                          rover.battery_type(),                ''),
            ('Battery Capacity',                      rover.battery_capacity(),            'Ah'),
            ('Battery Voltage',                       rover.battery_voltage(),             'V'),
            ('Battery Temperature',                   rover.battery_temperature(),         'C'),
            ('Controller Temperature',                rover.controller_temperature(),      'C'),
            ('Load Voltage',                          rover.load_voltage(),                'V'),
            ('Load Current',                          rover.load_current(),                'A'),
            ('Load Power',                            rover.load_power(),                  'W'),
            ('Charging Status',                       rover.charging_status_label(),       ''),
            ('Solar Voltage',                         rover.solar_voltage(),               'V'),
            ('Solar Current',                         rover.solar_current(),               'A'),
            ('Solar Power',                           rover.solar_power(),                 'W'),
            ('Energy Generated Today',                rover.energy_generation_today(),     'Wh'),
            ('Energy Consumed Today',                 rover.energy_consumption_today(),    'Wh'),
            ('Charging Today',                        rover.charging_amp_hours_today(),    'Ah'),
            ('Discharging Today',                     rover.discharging_amp_hours_today(), 'Ah'),
            ('Minimum Battery Voltage Today',         rover.battery_min_voltage_today(),   'V'),
            ('Maximum Battery Voltage Today',         rover.battery_max_voltage_today(),   'V'),
        ], f)
