#!/usr/bin/env python3
"""open-storm: martele l'ouverture du port USB (l'app plantee semble crasher dessus),
capte la fenetre ROM (/dev/cu.usbmodem201101) et flashe automatiquement."""
import os, random, serial, subprocess, sys, time

REPO = os.path.expanduser("~/dev/xteink-x4p-rescue")
BAUDS = [115200, 9600, 460800, 921600, 300]

def ports(prefix):
    try:
        return sorted("/dev/" + p for p in os.listdir("/dev") if p.startswith(prefix))
    except FileNotFoundError:
        return []

def esptool(args, timeout=90):
    return subprocess.run(["esptool", "--chip", "esp32s3", "--baud", "460800",
                           "--connect-attempts", "1", "--before", "no-reset",
                           "--after", "no-reset"] + args,
                          capture_output=True, text=True, timeout=timeout)

t0, i = time.time(), 0
while time.time() - t0 < 240:
    i += 1
    rom = ports("cu.usbmodem201101")
    if rom:
        port = rom[0]
        print(f"[{time.time()-t0:5.1f}s] FENETRE ROM sur {port} ! sync…", flush=True)
        r = esptool(["--port", port, "flash_id"])
        if "Detected flash" in (r.stdout + r.stderr):
            print("SYNC OK — download mode tenu", flush=True)
            w = esptool(["--port", port, "write_flash", "0x8000", f"{REPO}/ptable.bin"])
            print("ptable:", "OK" if w.returncode == 0 else w.stderr[-300:], flush=True)
            sys.exit(0)
        continue
    for ap in ports("cu.usbmodem"):
        try:
            s = serial.Serial(ap, random.choice(BAUDS), timeout=0.2,
                              xonxoff=random.random() < 0.3)
            s.setDTR(random.random() < 0.5)
            s.setRTS(random.random() < 0.5)
            time.sleep(0.1 + random.random() * 0.2)
            s.close()
        except Exception:
            pass
        break
    if i % 20 == 0:
        print(f"[{time.time()-t0:5.1f}s] {i} ouvertures, pas encore de fenetre…", flush=True)
    time.sleep(0.2)

print("storm terminé sans capture", flush=True)
sys.exit(1)
