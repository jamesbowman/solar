from astral import LocationInfo
from astral.location import Location
from datetime import datetime, timedelta

def solar_elevations(verbose = 0):
    city = LocationInfo("Pescadero", "USA", "America/Los_Angeles", 37.2552, -122.3830)
    loc = Location(city)

    date = datetime.now().date()

    start_of_day = datetime.combine(date, datetime.min.time())

    r = []
    for i in range(-1440, 0, 10):  # 1440 minutes in a day
        time = datetime.now() + timedelta(minutes=i)
        elevation = loc.solar_elevation(time)
        if verbose:
            print(f"Time: {time}, Solar Elevation: {elevation:.2f} degrees")
        r.append(elevation)
    return r

if __name__ == "__main__":
    solar_elevations(1)
