#!/usr/bin/env python3
"""jtag-crossink-rescue.py — réécriture complète via JTAG : ko.2@0x0 + ptable@0x8000 + CrossInk@0x10000."""
import os, socket, subprocess, sys, time

REPO = os.path.expanduser("~/dev/xteink-x4p-rescue")
OPENOCD = os.path.expanduser("~/dev/openocd-esp32/bin/openocd")
SCRIPTS = os.path.expanduser("~/dev/openocd-esp32/share/openocd/scripts")
KO = os.path.join(REPO, "CrossPoint-2.0.0-ko.2-x4pro-full.bin")
PTABLE = os.path.join(REPO, "ptable.bin")
CROSSINK = os.path.expanduser("~/dev/perso/xteink-x4p-rescue/extras/crossink/firmware-x4-pro-v2.0.0-959e3d1-RC.bin")

ocd = subprocess.Popen(
    [OPENOCD, "-s", SCRIPTS, "-f", "interface/esp_usb_jtag.cfg",
     "-f", "target/esp32s3.cfg", "-c", "adapter speed 5000"],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    for _ in range(30):
        try:
            s = socket.create_connection(("localhost", 4444), timeout=2); break
        except OSError:
            time.sleep(1)
    else:
        sys.exit("openocd ne répond pas")
    def cmd(c, wait):
        s.sendall(c.encode() + b"\r\n"); time.sleep(wait)
        s.setblocking(False); out = b""
        try:
            while True:
                d = s.recv(65536)
                if not d: break
                out += d
        except BlockingIOError:
            pass
        s.setblocking(True)
        txt = out.decode('utf-8','replace')
        print(f">>> {c[:80]}\n{txt[-350:]}", flush=True)
    cmd("reset halt", 6)
    cmd(f"program_esp {KO} 0x0 verify", 240)
    cmd(f"program_esp {PTABLE} 0x8000 verify", 40)
    cmd(f"program_esp {CROSSINK} 0x10000 verify reset", 240)
    print("OK — reset envoyé, l'app CrossInk doit démarrer (~30 s).", flush=True)
finally:
    ocd.terminate()
