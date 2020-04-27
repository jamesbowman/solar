import datetime
import math
import svgwrite

fake = [
[1587942012, 100, 13.2, 178.86]    ,
[1587942073, 87, 12.9, 90.9]       ,
[1587942133, 100, 13.2, 176.94]    ,
[1587942194, 100, 13.2, 176.96]    ,
[1587942254, 94, 13.0, 174.88]     ,
[1587942315, 87, 12.8, 122.91]     ,
[1587942375, 81, 12.9, 118.88]     ,
[1587942436, 96, 13.1, 172.0]      ,
[1587942497, 89, 12.9, 121.99]     ,
[1587942557, 93, 13.0, 171.97]     ,
[1587942618, 86, 13.0, 166.95]     ,
[1587942678, 94, 13.0, 166.96]     ,
[1587942739, 92, 13.0, 164.85]     ,
[1587942799, 91, 13.0, 160.92]     ,
[1587942860, 92, 13.0, 160.84]     ,
[1587942920, 93, 13.1, 157.89]     ,
[1587942981, 84, 13.0, 156.93]     ,
[1587943041, 95, 13.1, 154.88]     ,
[1587943102, 87, 13.0, 155.98]     ,
[1587943162, 89, 12.9, 152.96]     ,
[1587943223, 94, 13.0, 149.89]     ,
[1587943283, 92, 12.9, 150.86]     ,
[1587943344, 89, 12.9, 148.96]     ,
[1587943404, 94, 13.0, 146.88]     ,
[1587943465, 92, 12.9, 146.99]     ,
[1587943526, 86, 12.9, 143.93]     ,
[1587943586, 92, 13.0, 141.97]     ,
[1587943647, 92, 12.8, 141.92]     ,
[1587943707, 86, 12.9, 140.96]     ,
[1587943768, 89, 12.9, 136.96]     ,
[1587943828, 87, 12.9, 136.96]     ,
[1587943889, 84, 12.8, 136.0]      ,
[1587943949, 60, 12.3, 132.88]     ,
[1587944010, 85, 12.8, 133.95]     ,
[1587944070, 87, 12.9, 131.86]     ,
]

def redraw(datums):
    dwg = svgwrite.Drawing("graph.svg", size=(650, 400))

    args = {'fill':'red', 'stroke_opacity':0.0, 'stroke_width':.0}
    args = {'fill_opacity':0.0, 'stroke':'red', 'stroke_opacity':1.0, 'stroke_width':3}

    (times, soc, vb, pi) = [[d[i] for d in datums] for i in range(4)]
    t0 = min(times)
    t1 = max(times)
    def rescale(x, x0, x1, y0 = 0, y1 = 1):
        return y0 + ((x - x0) / (x1 - x0)) * (y1 - y0)
    def ongraph(x, y):
        return (50 + 575 * x, 350 - 349 * y)
    psoc = []
    pvb = []
    ppi = []
    for (t, s, v, p) in zip(times, soc, vb, pi):
        x = rescale(t, t0, t1)
        psoc.append(ongraph(x, rescale(s, 0, 100, 0, 1)))
        pvb.append(ongraph(x, rescale(v, 10.8, 14.7, 0, 1)))
        ppi.append(ongraph(x, rescale(p, 0, 600, 0, 1)))

    ticks = [i * (len(times) - 1) // 9 for i in range(10)]
    for i in ticks:
        t = times[i]
        ti = datetime.datetime.fromtimestamp(t)
        hhmm = "%02d:%02d" % (ti.hour, ti.minute)
        print(i, t, hhmm)
        x = rescale(t, t0, t1)
        dwg.add(dwg.line(ongraph(x, -.05), ongraph(x, 0), stroke="black", stroke_width="1"))
        dwg.add(dwg.text(hhmm, insert=ongraph(x, -.1), font_family="Arial", text_anchor = "middle"))

    args = {'fill':'black', 'stroke':'black', 'fill_opacity':0.2, 'stroke_width':2}
    poly = [ongraph(0,0)] + psoc + [ongraph(1,0)]
    dwg.add(dwg.polygon(poly, **args))

    args = {'stroke':'blue', 'fill_opacity':0.0, 'stroke_width':1}
    dwg.add(dwg.polyline(ppi, **args))

    dwg.save()

if __name__ == "__main__":
    redraw(fake)
