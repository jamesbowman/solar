import astral
import pytz
import datetime
import astral.sun

def sun():
    o = astral.Observer(latitude=37.2552, longitude=-122.3830, elevation=0.0)
    tzinfo = pytz.timezone("US/Pacific")
    s = astral.sun.sun(o)
    return {k:v.astimezone() for (k,v) in s.items()}

if __name__ == "__main__":
    s = sun()
    for k,v in s.items():
      print(k, v)
