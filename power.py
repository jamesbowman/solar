import time

def powerlog():
    db = []
    t0 = time.time()
    for fn in ("power.log.1", "power.log"):
        with open("/home/jamesb/tsd/" + fn) as f:
            for l in f:
                fields = l.split()
                if len(fields) == 5:
                    d = {}
                    po = float(fields[3].split('=')[1])
                    d = {"t" : float(fields[1]), "power" : po}
                    if d["t"] > (t0 - 24*60*60):
                        db.append(d)
    return db

if __name__ == "__main__":
    for d in powerlog():
        print(d)
