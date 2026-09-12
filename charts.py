import sys
import time
import math
import os

import numpy as np
from scipy.ndimage import gaussian_filter
import cairo

from PIL import Image, ImageDraw, ImageFont, ImageChops

import rt
import sunmoon
from sunalt import solar_elevations
import power

from chart_data import clean_samples, gap_limit, load_records, recorded_energy, smooth


def rescale(x, x0, x1, y0 = 0, y1 = 1):
    return y0 + ((x - x0) / (x1 - x0)) * (y1 - y0)
ap = 80
(X0, Y0, X1, Y1) = (ap, 260, 480-ap, 155)

def ongraph(x, y):
    return (rescale(x, 0, 1, X0, X1), rescale(y, 0, 1, Y0, Y1))

class Curve:
    def gpoint(self, t, q, d):
        return (q,
                rescale(t, self.t0, self.t1, X0, X1),
                rescale(d, self.d0, self.d1, Y0, Y1))

    def points(self):
        return [self.gpoint(t, q, d) if q > 0 and np.isfinite(d) else None
                for t, q, d in zip(self.times, self.quality, self.dd)]

    dmin = 999e9
    dmax = -999e9

    def ts(self, d):
        return d["t"]

    def get_datum(self, d):
        return d[self.datum]

    # None infers a gap threshold from the observed polling cadence (5–30 minutes).
    max_gap = None

    def db(self):
        return load_records(self.dir)

    def curve(self):
        self.t1 = time.time()
        self.t0 = self.t1 - 24*60*60
        samples = []
        for record in self.db():
            try:
                samples.append((self.ts(record), self.get_datum(record)))
            except (KeyError, TypeError, IndexError):
                # A record may be valid JSON but omit this chart's metric.
                continue
        self.samples = clean_samples(samples, self.t0, self.t1)
        self.gap_seconds = gap_limit(self.samples) if self.max_gap is None else self.max_gap
        self.times, self.quality, self.dd = smooth(
            self.samples, 120, self.t0, self.t1, self.gap_seconds)
        valid = self.valid()
        if not valid:
            return []
        self.d0 = min(self.dmin, min(valid))
        self.d1 = max(self.dmax, max(valid))
        if self.d0 == self.d1:
            padding = max(abs(self.d0) * 0.05, 0.5)
            self.d0 -= padding
            self.d1 += padding
        return self.points()

    def valid(self):
        return [v for v, q in zip(self.dd, self.quality) if q > 0 and np.isfinite(v)]

    def strvalue(self, d):
        return f"{d:.1f}"

TSDS = os.path.expanduser("~/tsd/")

DB_LITIME = load_records(TSDS + "litime")

class LiTime_Curve(Curve):
    def db(self):
        return DB_LITIME

class CairoSurface:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
        self.ctx = cairo.Context(self.surface)

    def asarray(self):
        r = np.ndarray(shape=(self.height, self.width, 4), dtype=np.uint8, buffer=self.surface.get_data())
        return r[:, :, :3] / 255

def gauss(ni, sigma):
    filtered_r = gaussian_filter(ni[:, :, 0], sigma=sigma)
    filtered_g = gaussian_filter(ni[:, :, 1], sigma=sigma)
    filtered_b = gaussian_filter(ni[:, :, 2], sigma=sigma)
    return np.stack([filtered_r, filtered_g, filtered_b], axis=2)

def sunalt():
    (width, height) = (480, 360)
    surface = CairoSurface(width, height)
    ctx = surface.ctx

    ctx.set_source_rgb(0, 0, 0)
    ctx.paint()

    sa = solar_elevations()

    ctx.set_line_width(3)
    for (i, e) in enumerate(sa):
        x = rescale(i, 0, len(sa), X0, X1)
        y = Y0
        if e > 0:
            ctx.set_source_rgb(0, rescale(e, 0, 45, .3, 1), 1)
        else:
            ctx.set_source_rgb(1, 0, 0)
        ctx.move_to(x, 0)
        ctx.line_to(x, height)
        ctx.stroke()

    return gauss(surface.asarray(), 10)

l_sunalt = (0.3 * sunalt() * rt.glow(.4))

fn = "IBMPlexSans-Medium.otf"
font1 = ImageFont.truetype(fn, 34)
font2 = ImageFont.truetype(fn, 20)

def center(draw, s, x, y, font):
    bbox = draw.textbbox((0, 0), s, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = x - (text_width) / 2
    y = y - (text_height) / 2

    draw.text((x, y), s, fill=(255,255,255), font=font)

class Tile:

    def __init__(self):
        
        # Set up the image dimensions
        width, height = 480, 360

        surface = CairoSurface(width, height)
        ctx = surface.ctx

        ctx.set_source_rgb(1, 1, 1)  # White
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.set_line_width(5)

        cc = self.curve()
        labels = []
        if cc:
            for p0, p1 in zip(cc, cc[1:]):
                if p0 is None or p1 is None:
                    continue
                _, x, y = p0
                ctx.move_to(x, y)
                _, x, y = p1
                ctx.line_to(x, y)
                ctx.stroke()
            # Isolated samples are dots, not invented line segments.
            for i, point in enumerate(cc):
                if point is not None and (i == 0 or cc[i - 1] is None) and (i == len(cc) - 1 or cc[i + 1] is None):
                    _, x, y = point
                    ctx.arc(x, y, 2.5, 0, 2 * math.pi)
                    ctx.fill()

            valid = self.valid()
            mn, mx = min(valid), max(valid)
            annotate = [(-.3, mx)]
            if mn != mx:
                annotate += [(.2, mn)]
            for yo, dpt in annotate:
                i = np.flatnonzero((self.quality > 0) & (self.dd == dpt))[-1]
                _, x, y = cc[i]
                ctx.arc(x, y, 6, 0, 2 * math.pi)
                ctx.fill()
                labels.append((self.strvalue(dpt), x, y + 100 * yo))

        l_line = surface.asarray()


        if 1:
            im = Image.new("RGB", (width, height))
            draw = ImageDraw.Draw(im)

            center(draw, self.title, width / 2, 50, font1)
            center(draw, self.subtitle(), width / 2, 90, font2)
            for (s, x, y) in labels:
                center(draw, s, x, y, font2)

            l_text = np.array(im) / 255

        l_glow = gaussian_filter(l_text + l_line, sigma=12)

        final = (
                 l_sunalt +
                 0.5 * l_glow +
                 1.0 * l_text +
                 1.0 * l_line 
                 )
        final = np.minimum(255, np.maximum(final * 255, 0)).astype(np.uint8)
        self.im = Image.fromarray(final)

    def subtitle(self):
        return "" if self.valid() else "No data"

class ReportMJ:
    def subtitle(self):
        energy, duration = recorded_energy(self.samples, self.gap_seconds)
        if not duration:
            return "No data" if not self.samples else "Insufficient data"
        return f"{energy / 1e6:.1f} MJ"

if 1:
    class Main_Power(ReportMJ, Tile, LiTime_Curve):
        title = "Charging Power (W)"
        dir = TSDS + "litime"
        datum = "battery_power_w"
        pos = (1, 0)
        dmin = 0
        dmax = 200
        def strvalue(self, d):
            return f"{d:.0f}"

if 1:
    class Inverter(ReportMJ, Tile, Curve):
        title = "Inverter (W)"
        dir = TSDS + "shellyplugus-d4d4da092de4/status/switch:0"
        pos = (2, 0)
        def ts(self, d):
            if "minute_ts" in d["aenergy"]:
                return d["aenergy"]["minute_ts"]
            return 0
        def get_datum(self, d):
            return d["aenergy"]["by_minute"][1] * 0.060
        dmin = 0
        dmax = 200

if 0:
    class Grid(ReportMJ, Tile, Curve):
        def db(self):
            return power.powerlog()
        datum = "power"
        title = "Grid Use (W)"
        pos = (3, 0)
        dmin = 0
        dmax = 200
elif 1:
    class Solar_V(Tile, LiTime_Curve):
        title = "Panel Voltage (V)"
        datum = "panel_voltage_v"
        pos = (0, 1)
        dmin = 0
        dmax = 100
elif 0:
    class Battery_Current(Tile, Curve):
        title = "Battery Current (A)"
        dir = TSDS + "sungauge40"
        datum = "current"
        pos = (3,0)
        svgname = "graph_k.svg"
        dmin = 6
        dmax = 30
        def subtitle(self):
            avg_a = np.mean([y for (x,y) in self.samples])
            ah = 24 * avg_a
            return f"{ah:+.0f} Ah"

class Main_V(Tile, LiTime_Curve):
    title = "Main Battery (V)"
    dir = TSDS + "litime"
    datum = "battery_voltage_v"
    pos = (1, 1)
    dmin = 11.8
    dmax = 14.7

if 0:
    class main_SOC(Tile, Curve):
        title = "Main SOC (Ah)"
        dir = TSDS + "sungauge40"
        datum = "soc"
        pos = (1, 1)
        # dmin = 0
        # dmax = 280
        def strvalue(self, d):
            return f"{d:.0f}"
        def get_datum(self, d):
            return d.get("soc", 280)

class Coop_V(Tile, Curve):
    title = "Coop Battery (V)"
    dir = TSDS + "coop"
    datum = "vbatt"
    svgname = "graph_i.svg"
    pos = (3, 0)
    dmin = 11
    dmax = 15

class HouseAC(ReportMJ, Tile, Curve):
    title = "House Power (kW)"
    dir = TSDS + "houseac"
    datum = "power"
    pos = (2, 1)
    dmin = 0
    def strvalue(self, d):
        return f"{d / 1000:.1f}"

class Coop_Temp(Tile, Curve):
    title = "Coop (°C)"
    dir = TSDS + "coop"
    datum = "temp"
    pos = (3, 2)
    dmin = 6
    dmax = 30

class Coop_Door(Tile, Curve):
    title = "Coop Door"
    dir = TSDS + "coop"
    datum = "dooropen"
    pos = (3, 1)
    dmin = 0
    dmax = 1
    def strvalue(self, d):
        return ["closed", "open"][int(round(d))]

class Main_Temp(Tile, Curve):
    title = "Shed (°C)"
    dir = TSDS + "sungauge40"
    datum = "temp"
    pos = (2,2)
    svgname = "graph_k.svg"
    dmin = 6
    dmax = 30

# class Controller_Temp(Draw, Curve):
#     title = "Controller (°C)"
#     dir = TSDS + "litime"
#     datum = "controller_temperature_c"
#     svgname = "graph_k.svg"
#     dmin = 6
#     dmax = 30

class Upstairs_Temp(Tile, Curve):
    title = "Upstairs (°C)"
    dir = TSDS + "bedroom"
    datum = "temp"
    svgname = "graph_l.svg"
    pos = (1, 2)
    dmin = 6
    dmax = 30

class Pressure(Tile, Curve):
    title = "Pressure (hPa)"
    dir = TSDS + "bedroom"
    datum = "pressure"
    pos = (0, 2)
    dmin = 1010
    dmax = 1030
    def strvalue(self, d):
        return f"{d:.0f}"

if 1:
    class TimeStamp(Tile):
        pos = (0, 0)
        def __init__(self):
            (width, height) = (480, 360)
            im = Image.new("RGB", (width, height))
            draw = ImageDraw.Draw(im)

            s = time.strftime("%H:%M %Z", time.localtime())
            center(draw, s, width / 2, 50, font1)

            s = sunmoon.sun()
            W = 300
            for i,k in enumerate(("dawn", "noon", "dusk")):
                x = ((480 - W) // 2) + i * W // 2
                center(draw, k, x, 280, font2)
                v = s[k].strftime("%H:%M")
                center(draw, v, x, 320, font2)
            l_text = np.array(im) / 255

            l_glow = gaussian_filter(l_text, sigma=12)

            try:
                map = np.array(Image.open("2400x2400.jpg").crop((440, 1058, 440 + 480, 1058 + 360))) / 255.0
            except:
                map = 0

            final = (map * np.array((.8, .8, 1)) * rt.glow(0.40) +
                     0.5 * l_glow +
                     1.0 * l_text
                     )
            final = np.minimum(255, np.maximum(final * 255, 0)).astype(np.uint8)
            self.im = Image.fromarray(final)
else:
    class TimeStamp(Tile):
        pos = (0, 0)
        def __init__(self):
            map = np.array(Image.open("2400x2400.jpg").crop((440, 1058, 440 + 480, 1058 + 360)))
            final = (map * np.array((1, 1, 1)) * rt.glow(0.50)).astype(np.uint8)
            self.im = Image.fromarray(final)

if __name__ == "__main__":
    if 0:
        x = Inverter()
        x.im.save("out.png")
        sys.exit(0)

    final = Image.new("RGB", (1920, 1080))
    tiles = [tc() for tc in Tile.__subclasses__()]
    for t in tiles:
        final.paste(t.im, (480 * t.pos[0], 360 * t.pos[1]))
    final.save("out.png")
