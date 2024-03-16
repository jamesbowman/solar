import time
import os
import json
from renogy_rover import RenogyRover
from render import redraw

def MJ(wh):
    return round(wh * 3600 / 1e6, 1)

if __name__ == "__main__":
    portname="/dev/serial/by-id/usb-FTDI_FT232R_USB_UART_A9GIWNYB-if00-port0"
    rover = RenogyRover(portname, 1)
    while True:
        t = time.time()
        d = [
            int(t),
            rover.battery_percentage(),
            rover.battery_voltage(),
            round(rover.solar_voltage() * rover.solar_current(), 2)
        ]
        print(d)
        with open("log" ,"a") as f:
            f.write(repr(d) + "\n")
        with open("tmp", 'w') as f:
            json.dump({
                't':                                    t,
                'SOC':                                  rover.battery_percentage(),          
                'Battery Voltage':                      rover.battery_voltage(),             
                'Battery Temperature':                  rover.battery_temperature(),         
                'Controller Temperature':               rover.controller_temperature(),      

                'Solar Voltage':                        rover.solar_voltage(),               
                'Solar Current':                        rover.solar_current(),               
                'Solar Power':                          rover.solar_power(),                 
                'Charging Status':                      rover.charging_status_label(),       

                'Load Voltage':                         rover.load_voltage(),                
                'Load Current':                         rover.load_current(),                
                'Load Power':                           rover.load_power(),                  

                'Energy Generated Today':               rover.energy_generation_today(),     
                'Energy Consumed Today':                rover.energy_consumption_today(),    
                'Charging Today':                       rover.charging_amp_hours_today(),    
                'Discharging Today':                    rover.discharging_amp_hours_today(), 
                'Battery Minimum Today':                rover.battery_min_voltage_today(),   
                'Battery Maximum Today':                rover.battery_max_voltage_today(),   
            }, f)
        os.rename("tmp", f"/home/jamesb/tsd/renogy/{t:.6f}.json")
        with open('html/instantaneous.json', 'w') as f:
            json.dump([
                ('SOC',                                   rover.battery_percentage(),          '%'),
                ('Battery Voltage',                       rover.battery_voltage(),             'V'),
                ('Battery Temperature',                   rover.battery_temperature(),         'C'),
                ('Controller Temperature',                rover.controller_temperature(),      'C'),

                ('Solar Voltage',                         rover.solar_voltage(),               'V'),
                ('Solar Current',                         rover.solar_current(),               'A'),
                ('Solar Power',                           rover.solar_power(),                 'W'),
                ('Charging Status',                       rover.charging_status_label(),       ''),

                ('Load Voltage',                          rover.load_voltage(),                'V'),
                ('Load Current',                          rover.load_current(),                'A'),
                ('Load Power',                            rover.load_power(),                  'W'),

                ('Energy Generated Today',                MJ(rover.energy_generation_today()), 'MJ'),
                ('Energy Consumed Today',                 MJ(rover.energy_consumption_today()),'MJ'),
                ('Charging Today',                        rover.charging_amp_hours_today(),    'Ah'),
                ('Discharging Today',                     rover.discharging_amp_hours_today(), 'Ah'),
                ('Battery Minimum Today',                 rover.battery_min_voltage_today(),   'V'),
                ('Battery Maximum Today',                 rover.battery_max_voltage_today(),   'V'),

                ('Cumulative',                            rover.energy_generation_cumulative() / 1000,'kWh'),
            ], f)
        ll = [l for l in open("log")][-2000:]
        db = [eval(l) for l in ll]
        redraw(db)
        d = -time.time() % 60
        print('sleep', d)
        time.sleep(d)
