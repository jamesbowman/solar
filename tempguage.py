import sys
import struct
import time
import datetime
import i2cdriver, EDS

import logging
import sensor_mqtt

def sleep_until_next_minute():
    now = datetime.datetime.now()
    next_minute = (now + datetime.timedelta(minutes=1)).replace(second=0, microsecond=0)
    sleep_duration = (next_minute - now).total_seconds()
    time.sleep(sleep_duration)

def tempgauge():
    i2=i2cdriver.I2CDriver(sys.argv[1])
    i2.scan()
    with sensor_mqtt.connection() as client:
        d = EDS.Temp(i2)
        while 1:
            s = dict()
            s["t"] = time.time()
            try:
                s["temp"] = d.read()
            except struct.error:
                continue
            sensor_mqtt.publish(client, "sungauge40", s)
            sleep_until_next_minute()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    tempgauge()
